# 0003-django. 학교 통합 로그인(OIDC)은 allauth `openid_connect` 대신 자체 클라이언트로 한다

- 상태: 채택 (2026-10-24, Phase 2)
- 관련: [이식 계획 7.1절](../porting-plan.md), 원본 [ADR 0007](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0007-people-accounts-and-sign-in.md) "SSO 구현"

## 배경

이식 계획 7.1절은 SSO를 django-allauth `socialaccount`의 `openid_connect` 제공자로 하고, 제공자 설정을 `AuthenticationSettings.sso_providers`(DB)에서 읽는 어댑터를 두기로 했다. Phase 2에서 allauth 65.20.1의 구현을 확인한 결과 원본의 요구와 두 가지가 다르다.

| 원본 요구 (ADR 0007) | allauth `openid_connect` |
|---|---|
| authorization code + PKCE(S256), state, **nonce** | PKCE는 설정으로 켤 수 있으나 nonce를 보내지도 확인하지도 않는다 |
| ID 토큰을 **항상** 제공자 JWKS로 서명·issuer·audience·만료·nonce까지 검증 | 토큰 엔드포인트에서 직접 받은 ID 토큰은 서명 검증을 건너뛴다(OIDC Core 3.1.3.7의 허용 조항) |
| 연결은 `user_identities`(provider, subject)에 저장 | 연결은 `socialaccount_socialaccount`에 저장하고 회원가입 흐름(SocialLogin)을 거친다 |
| SSO 로그인만으로 계정을 만들지 않음, 학교 이메일 자동 연결, 신뢰하지 않는 제공자는 2단계 인증 | 어댑터 훅(`pre_social_login`)으로 가능하지만 흐름 전체를 덮어써야 한다 |

원본 테스트 `SignInMethodsTest`는 잘못된 nonce·audience·issuer의 토큰을 거부하는지 확인한다. allauth 제공자를 그대로 쓰면 nonce 사례가 통과할 수 없고, 서명 검증 생략은 원본보다 약한 보안 수준이다.

## 결정

1. OIDC 흐름은 원본 `OidcClient`와 같은 작은 자체 클라이언트(`ninefruits.security.services.oidc.OidcClient`, httpx + PyJWT)로 한다. discovery(`/.well-known/openid-configuration`, 1시간 캐시), PKCE S256, state·nonce를 세션에 두고, ID 토큰은 JWKS로 서명(RS256)·issuer·audience·만료(60초 허용 오차)·nonce를 로컬에서 검증한다. PyJWT는 allauth `socialaccount`가 이미 의존하는 패키지라 의존성이 늘지 않는다.
2. 경로는 `/auth/sso/<key>/redirect/`, `/auth/sso/<key>/callback/`(이름 `sso_redirect`, `sso_callback`)이다. 관리 화면 **설정 > 로그인 수단**이 제공자에 등록할 리디렉션 URI로 이 주소를 보여 준다.
3. 로그인 성공 뒤에는 allauth의 로그인 단계(`perform_login` + `Login`)를 그대로 쓴다. 따라서 2단계 인증 단계(`TwoFactorChallengeStage`), 기기 기억, 로그인 보안 이벤트, 세션 처리가 비밀번호 로그인과 같다. 제공자의 `trusts_mfa`가 켜져 있으면 `Login.state["sso_trusts_mfa"]`로 2단계 인증 단계만 건너뛴다.
4. 연결은 원본과 같이 `user_identities`에만 둔다(`LinkIdentity`, `UnlinkIdentity`). allauth `socialaccount` 앱과 `openid_connect` 제공자는 `INSTALLED_APPS`에 남아 있지만(테이블은 0001-django의 스키마에 있음) `SocialApp`을 만들지 않으므로 쓰이지 않는다. 회원가입은 `SocialAccountAdapter.is_open_for_signup = False`로 닫혀 있다.

## 결과

- 원본 `SignInMethodsTest`의 SSO 사례(연결된 계정 로그인, audience·nonce·issuer 거부, 학교 이메일 자동 연결, SSO 뒤 2단계 인증)가 가짜 제공자(httpx `MockTransport`)로 그대로 통과한다.
- 제공자별 패키지 없이 Entra ID, Google Workspace, Keycloak을 같은 코드로 쓴다. SAML은 원본과 같이 범위 밖이다.
- allauth를 올릴 때 이 흐름은 영향을 받지 않는다. 대신 OIDC 클라이언트 유지 보수(키 교체 시 JWKS 캐시 1시간)는 이 저장소의 몫이다.
