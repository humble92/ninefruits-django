# 0004-django. API 연동 토큰은 django-rest-knox로 한다

- 상태: 채택 (2026-10-24, Phase 12)
- 관련: [이식 계획 12절](../porting-plan.md#12-lms-연동과-api)·18절 5번, 원본 [ADR 0017](https://github.com/humble92/ninefruits-laravel/blob/main/porting/decisions/0017-lms-integration.md), [LMS 연동 가이드](../../docs/lms-integration-guide.md)

## 배경

원본 Laravel에는 외부에 열린 API가 없었다(Sanctum 미설치, `routes/api.php` 없음). 이식 계획 12절은 Django 쪽에서 DRF `api/v1/`을 처음 열고, 인증을 세션(포털 HTMX 보조 조회) + 토큰(연동용)으로 하되 토큰 방식을 **django-rest-knox**와 DRF 기본 토큰(`rest_framework.authtoken`) 중에서 Phase 12에 정하기로 했다(18절 5번, 기본 가정 knox). Phase 0에서 knox 5.1.0이 이미 설치되어 `knox_authtoken` 표가 만들어져 있었다(스키마 비교에서 빠지는 Django 쪽 표, ADR 0001-django).

토큰의 쓰임은 사람의 화면 로그인이 아니라 **연동 계정**이다. LMS(콜백·점수 전달), BI 도구(reporting 뷰 읽기), 증명서 확인 같은 외부 시스템이 필요한 권한만 가진 서비스 계정으로 호출한다.

| 기준 | DRF `authtoken` | knox |
|---|---|---|
| 저장 | 토큰 원문을 그대로 저장(DB 유출 = 토큰 유출) | SHA-512 다이제스트만 저장, 원문은 발급 때 한 번만 보임 |
| 계정당 토큰 | 1개(교체하면 모든 연동이 함께 끊김) | 여러 개(연동마다 따로 발급·회수) |
| 만료 | 없음 | 토큰마다 만료 시각, 만료 토큰은 인증 시 삭제 |
| 회수 | 계정의 토큰 삭제 | 토큰 하나 또는 전부 |
| 의존성 | DRF 내장 | 이미 설치됨(Phase 0) |

## 결정

1. 연동 토큰은 knox로 한다. 인증 헤더는 `Authorization: Token <token>`이다. `rest_framework.authtoken`은 설치하지 않는다.
2. 인증 클래스 순서는 토큰 → 세션이다(`REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES`). 인증이 없으면 401과 `WWW-Authenticate: Token`을 돌려준다. 세션 요청은 CSRF를 검사한다(DRF `SessionAuthentication`).
3. 토큰 요청은 DRF가 뷰 안에서 인증하므로 `SetDatabaseSessionContextMiddleware`가 이미 지나간 뒤다. `ninefruits.api.authentication.TokenAuthentication`이 인증 직후 요청 컨텍스트와 DB 세션 컨텍스트(`app.user_id`)를 토큰의 사용자로 맞춘다. 따라서 토큰 요청도 RLS, 데이터 감사 트리거, 업무 감사에서 그 사용자로 보인다. 요청이 끝나면 미들웨어가 컨텍스트를 초기화한다.
4. 토큰은 그 사용자의 권한(카탈로그 권한과 범위)을 그대로 가진다. 연동마다 필요한 권한만 가진 서비스 계정을 만들고(`lms.manage`, `reports.view`) 그 계정의 토큰을 쓴다. 비활성 계정의 토큰은 거부된다(knox).
5. 발급
   - 운영자: `uv run manage.py api_issue_token <email> --days=N --reason=... --actor=...`. 토큰은 표준 출력에 한 번만 나온다.
   - 본인: `POST /api/v1/auth/tokens/`(`{"days": 90, "note": "..."}`). **세션 인증으로만** 가능하다(`SessionOnly`). 토큰으로 토큰을 만들 수 없으므로 모든 토큰은 2단계 인증 정책을 거친 화면 로그인에서 시작한다. 다른 계정의 토큰 발급은 `users.update`가 필요하다(`IssueApiToken`).
   - 수명: 기본 90일(`API_TOKEN_TTL_DAYS`, knox `TOKEN_TTL`), 1~365일. 자동 연장(`AUTO_REFRESH`)은 끈다. 만료 없는 토큰은 만들지 않는다.
6. 회수: `DELETE /api/v1/auth/tokens/current/`(이 요청의 토큰), `DELETE /api/v1/auth/tokens/<key>/`(본인 토큰 하나), `uv run manage.py api_revoke_tokens <email> [--key=...]`(운영자, `--list`로 목록).
7. 감사: 발급과 회수는 업무 감사(`audit.activity_log`, 로그 이름 `api`)의 `api.token_issued`·`api.token_revoked`로 남는다. 속성에는 토큰 키 접두(앞 15자, 조회용이며 인증에 쓸 수 없음)와 만료 시각만 두고, 토큰 원문과 다이제스트는 남기지 않는다. 명령 실행은 `AuditedCommand`의 `command.executed`에도 남는다.
8. 요청 제한(DRF throttle): 익명(주소별) `anon` 30/분, 세션 사용자(계정별) `user` 120/분, 연동 토큰(토큰별) `integration` 600/분. 한 요청은 셋 중 하나로만 센다. 값은 환경 변수 `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`으로 바꾼다.
9. 스키마와 문서: drf-spectacular. OpenAPI 스키마 `/api/schema/`는 로그인한 사용자(세션·토큰), Swagger UI `/api/docs/`는 `admin_panel.access` 권한자만 연다. Swagger UI 자산은 drf-spectacular-sidecar로 이 사이트에서 내보내고 초기화 스크립트를 별도 요청으로 받아(`SpectacularSwaggerSplitView`) 포털의 CSP(외부 스크립트와 인라인 스크립트 금지)를 그대로 지킨다.

## 결과

- DB가 유출되어도 토큰을 쓸 수 없고, 연동별로 끊을 수 있다. 토큰 표(`knox_authtoken`)는 Django 쪽 표라 원본과의 스키마 동등성에 영향이 없다.
- 계정의 권한·범위·RLS가 API에도 그대로 적용되므로 API용 별도 권한 모델이 없다. 권한 이름은 카탈로그 그대로(`HasCatalogPermission("lms.manage")`).
- 토큰 관리 화면(관리 화면 목록·발급)은 만들지 않았다. 발급·회수는 명령과 API로 한다. 필요해지면 **사용자와 접근** 그룹에 화면을 추가한다.
- 원본에 대응 기능이 없으므로 원본과의 동등성 비교 대상이 아니다. 테스트는 `tests/api/test_api.py`(인증, 권한, throttle, 스키마 접근).
