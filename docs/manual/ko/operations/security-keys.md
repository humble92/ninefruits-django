# 키 관리

- 대상: IT 운영자
- 관련: [설치](installation.md), [명령 레퍼런스](commands.md)

| 키 | 용도 | 잃어버리면 | 교체 |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | 세션, CSRF, 서명(비밀번호 재설정 링크, 이메일 인증 링크, 기기 기억 쿠키), 2단계 인증 비밀값(인증 앱 TOTP 비밀값, 복구 코드)과 SSO 클라이언트 비밀값의 암호화 | 모든 사용자 로그아웃, 발송된 링크 무효, 등록된 인증 앱과 복구 코드 사용 불가(사용자별 2단계 인증 초기화 필요) | 원칙적으로 교체하지 않는다. 교체 절차(이전 키로 복호화 후 재암호화)는 Phase 13에서 정한다 |
| `PII_ENCRYPTION_KEY` | 신분증번호 등 개인정보 암호화(AES-256-GCM) | **암호화된 개인정보 복구 불가** | 아래 절차 |
| `PII_HASH_KEY` | 개인정보 정확 일치 검색 해시(HMAC-SHA256) | 검색 불가(데이터는 남음) | 원칙적으로 교체하지 않음 |

`DJANGO_SECRET_KEY`는 `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`, 개인정보 키 두 개는 `uv run manage.py pii_generate_key`로 만든다.

보관 원칙

- 세 키는 서버의 환경 설정과 별도로 비밀 저장소(Vault, 클라우드 비밀 관리자 등)나 오프라인 봉인 보관에 두 벌 이상 보관한다.
- 백업 파일과 같은 위치에 두지 않는다. DB 백업이 유출되어도 개인정보는 키 없이 읽을 수 없어야 한다.
- 개발용 `.env`와 테스트 설정의 키를 운영에 쓰지 않는다.

## 개인정보 키 교체 절차

1. `uv run manage.py pii_generate_key`로 새 키를 만든다(출력의 `PII_ENCRYPTION_KEY`만 사용).
2. 현재 키를 `PII_PREVIOUS_KEYS`에 넣고(쉼표로 여러 개), 새 키를 `PII_ENCRYPTION_KEY`에 넣는다.
3. 설정을 다시 읽게 한다: gunicorn과 Celery 워커를 다시 시작한다(Docker: `docker compose restart app worker beat`).
4. 개인정보 모델마다 `uv run manage.py pii_reencrypt {앱.모델} --dry-run`(예: `person.Person`)으로 대상 건수를 확인하고 `--force` 없이 실행한다(확인 질문에 답한다).
5. Flower에서 작업 완료를 확인한 뒤 `--dry-run` 결과가 0이 되면 `PII_PREVIOUS_KEYS`에서 이전 키를 지운다.
6. 이전 키는 백업 보존 기간 동안 봉인 보관한다(이전 백업을 복원할 때 필요).
