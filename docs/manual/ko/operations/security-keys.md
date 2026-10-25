# 키 관리

- 대상: IT 운영자
- 관련: [설치](installation.md), [명령 레퍼런스](commands.md), [배포 체크리스트](deployment-checklist.md)

| 키 | 용도 | 잃어버리면 | 교체 |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | 세션, CSRF, 서명(비밀번호 재설정 링크, 이메일 인증 링크, 기기 기억 쿠키), 이메일 2단계 코드 해시, 2단계 인증 비밀값(인증 앱 TOTP 비밀값, 복구 코드)과 SSO 클라이언트 비밀값의 암호화 | 모든 사용자 로그아웃, 발송된 링크 무효, 등록된 인증 앱과 복구 코드 사용 불가(사용자별 2단계 인증 초기화 필요), SSO 클라이언트 비밀값 다시 입력 | `DJANGO_SECRET_KEY_FALLBACKS`에 이전 키를 두고 교체(아래 절차) |
| `PII_ENCRYPTION_KEY` | 신분증번호 등 개인정보 암호화(AES-256-GCM) | **암호화된 개인정보 복구 불가** | `PII_PREVIOUS_KEYS`에 이전 키를 두고 교체(아래 절차) |
| `PII_HASH_KEY` | 개인정보 정확 일치 검색 해시(HMAC-SHA256) | 검색 불가(데이터는 남음) | 원칙적으로 교체하지 않음 |

`DJANGO_SECRET_KEY`는 `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`, 개인정보 키 두 개는 `uv run manage.py pii_generate_key`로 만든다.

보관 원칙

- 세 키는 서버의 환경 설정과 별도로 비밀 저장소(Vault, 클라우드 비밀 관리자 등)나 오프라인 봉인 보관에 두 벌 이상 보관한다.
- 백업 파일과 같은 위치에 두지 않는다. DB 백업이 유출되어도 개인정보는 키 없이 읽을 수 없어야 한다.
- 개발용 `.env`와 테스트 설정의 키를 운영에 쓰지 않는다.
- 웹(gunicorn), Celery 워커, Celery beat는 모두 같은 키 값을 읽어야 한다. 키를 바꾼 뒤에는 세 프로세스를 함께 다시 시작한다.

## `DJANGO_SECRET_KEY` 교체 절차

정기 교체나 담당자 변경 때 쓴다. Django의 `SECRET_KEY_FALLBACKS`를 쓰므로 이전 키가 남아 있는 동안 사용자는 로그아웃되지 않는다. 원본(Laravel)의 `APP_PREVIOUS_KEYS`와 같은 방식이다.

1. 새 키를 만든다: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`.
2. 현재 키를 `DJANGO_SECRET_KEY_FALLBACKS`의 맨 앞에 넣고(쉼표로 여러 개), 새 키를 `DJANGO_SECRET_KEY`에 넣는다.
   ```
   DJANGO_SECRET_KEY=<새 키>
   DJANGO_SECRET_KEY_FALLBACKS=<이전 키>
   ```
3. gunicorn, Celery 워커, beat를 다시 시작한다(Docker: `docker compose restart app worker beat`).
4. 2단계 인증 비밀값과 SSO 클라이언트 비밀값을 새 키로 다시 암호화한다. `uv run manage.py security_reencrypt_secrets --dry-run`으로 건수를 확인하고 `--dry-run` 없이 실행한 뒤, 다시 `--dry-run`이 0을 보고하는지 확인한다. 이 단계 전에 이전 키를 지우면 인증 앱과 복구 코드를 쓸 수 없게 된다.
5. 이전 키를 남겨 두는 기간을 정한다. 아래 항목은 이전 키가 남아 있는 동안에만 유효하다.

   | 항목 | 이전 키가 남아 있는 동안 | 이전 키를 지운 뒤 |
   |---|---|---|
   | 로그인 세션 | 교체 뒤 첫 요청에서 새 키로 옮겨진다 | 그동안 접속하지 않은 세션만 로그아웃된다 |
   | 비밀번호 재설정 링크, 이메일 인증 링크 | 유효(3일) | 다시 요청해야 한다 |
   | 기기 기억 쿠키 | 유효(보안 설정의 기억 일수, 기본 30일) | 다음 로그인 때 2단계 인증을 다시 묻는다 |
   | 이메일 2단계 코드 | 교체 직전에 보낸 코드는 맞지 않는다(유효 10분) | 같음 |

   보통 3일 이상, 기기 기억을 유지하려면 기억 일수만큼 남겨 둔다.
6. 기간이 끝나면 `DJANGO_SECRET_KEY_FALLBACKS`에서 이전 키를 지우고 3번처럼 다시 시작한다.
7. 이전 키는 백업 보존 기간 동안 봉인 보관한다. 이전 백업에 든 2단계 인증 비밀값은 그 키로 암호화되어 있다. 이전 백업을 복원하면 그 키를 `DJANGO_SECRET_KEY_FALLBACKS`에 넣고 4번을 실행한다.

### 키가 유출되었을 때

1. 위 1~4번을 바로 실행한다(이전 키는 4번의 재암호화에만 필요하다).
2. 4번이 끝나면 곧바로 이전 키를 지우고 다시 시작한다. 모든 세션이 끝나고 발송된 링크와 기기 기억이 무효가 된다(의도한 결과).
3. 보안 로그에서 유출 기간의 로그인과 관리 작업을 확인한다([감사와 유지보수](audit-and-maintenance.md)).

## 개인정보 키 교체 절차

1. `uv run manage.py pii_generate_key`로 새 키를 만든다(출력의 `PII_ENCRYPTION_KEY`만 사용).
2. 현재 키를 `PII_PREVIOUS_KEYS`에 넣고(쉼표로 여러 개), 새 키를 `PII_ENCRYPTION_KEY`에 넣는다.
3. 설정을 다시 읽게 한다: gunicorn과 Celery 워커를 다시 시작한다(Docker: `docker compose restart app worker beat`).
4. 개인정보 모델마다 `uv run manage.py pii_reencrypt {앱.모델} --dry-run`(예: `person.Person`)으로 대상 건수를 확인하고 `--force` 없이 실행한다(확인 질문에 답한다).
5. Flower에서 작업 완료를 확인한 뒤 `--dry-run` 결과가 0이 되면 `PII_PREVIOUS_KEYS`에서 이전 키를 지운다.
6. 이전 키는 백업 보존 기간 동안 봉인 보관한다(이전 백업을 복원할 때 필요).

`PII_HASH_KEY`를 바꾸면 저장된 검색 해시가 모두 맞지 않게 되어 신분증번호·여권번호 정확 일치 검색이 실패한다. 원칙적으로 바꾸지 않는다.
