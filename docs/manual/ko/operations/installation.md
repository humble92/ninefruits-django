# 설치

- 대상: IT 운영자
- 관련: [명령 레퍼런스](commands.md), [키 관리](security-keys.md)

## 1. 요구 사항

| 구성 요소 | 버전 | 비고 |
|---|---|---|
| Python | 3.14 | [uv](https://docs.astral.sh/uv/)로 설치·실행한다(`uv sync`). 시스템 패키지: `gettext`(번역 컴파일), `libmagic`(파일 형식 판별) |
| Node.js | 22 | 화면 자산 빌드(`npm ci && npm run build`). 운영 서버에는 빌드 결과만 있으면 된다 |
| PostgreSQL | 18 | `btree_gist`, `pg_trgm` 확장(마이그레이션이 설치), ICU collation |
| Redis | 8 | 캐시, Celery 브로커와 결과 |
| Gotenberg | 8 | PDF 생성. 내부망에만 노출 |
| 메일 서버 | SMTP | 비밀번호 재설정, 2단계 인증 이메일 코드 |
| 웹 서버 | gunicorn + Nginx | `uv run gunicorn config.wsgi`. Nginx는 `staticfiles/`를 직접 제공하고 나머지를 gunicorn으로 넘긴다 |
| 큐 워커 | Celery worker | `uv run celery -A config worker`를 프로세스 관리자(systemd, supervisor)로 상시 실행 |
| 스케줄러 | Celery beat | `uv run celery -A config beat` 한 대만 실행(DB 스케줄러, django-celery-beat) |
| 큐 모니터 | Flower (선택) | `uv run celery -A config flower`. `큐 모니터 조회` 권한이 있는 사용자만 접근하도록 Nginx 뒤에 둔다 |

## 2. 데이터베이스 준비

DB 슈퍼유저가 한 번 실행한다. 애플리케이션은 슈퍼유저를 쓰지 않는다.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| 역할 | 환경 변수 | 용도 |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | 애플리케이션 실행(행 단위 보안 적용, DDL 불가) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | 마이그레이션만(`migrate`가 자동으로 이 연결을 쓴다) |
| `app_reporting` | (BI 도구에 설정) | `reporting` 스키마 조회 |

Docker Compose 개발 환경에서는 `pgsql` 컨테이너가 처음 시작할 때 `docker/pgsql/20-create-app-roles.sh`가 같은 일을 한다(역할 생성, `ninefruits`와 테스트 DB 준비).

## 3. 환경 설정

`.env.example`을 `.env`로 복사해 값을 채운다(운영에서는 환경 변수나 비밀 저장소로 넣는다). 반드시 바꿀 값

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. [키 관리](security-keys.md)에 따라 보관한다.
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **분실하면 암호화된 개인정보를 복구할 수 없다.** [키 관리](security-keys.md)에 따라 별도 보관한다.
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `INSTITUTION_TIMEZONE`: 최초 설치 시 기관 시간대 기본값(예: `Asia/Seoul`)

## 4. 설치

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py migrate                    # app_migrator 연결로 스키마와 데이터 마이그레이션
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py security_sync_permissions  # 권한 카탈로그를 DB에 맞춘다
echo "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator \
    --email=admin@example.ac.kr --name="관리자" --password-stdin
```

Django `createsuperuser`는 비활성화되어 있다. 최초 관리자는 `security_create_administrator`로만 만든다([명령 레퍼런스](commands.md)). 이 명령은 시스템 관리자 역할(필수 데이터)이 있어야 하며, 없으면 무엇을 먼저 실행할지 안내한다. Phase 1부터는 `setup_install`이 마이그레이션, 필수 데이터, 기관 기본 설정, 설치 프로파일, 최초 관리자를 차례로 처리한다.

설치 후 업무 관리자는 [관리자 매뉴얼 5장 초기 세팅 순서](../admin/05-institution-setup.md)에 따라 기준정보를 입력한다.

### Docker Compose (개발)

```bash
cp .env.example .env
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py migrate
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py security_sync_permissions
docker compose exec app uv run manage.py security_create_administrator --email=admin@example.test --name="관리자"
```

| 서비스 | 주소 |
|---|---|
| 애플리케이션 | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit(개발용 메일함) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite 개발 서버(선택, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

## 5. 설치 확인

1. `/accounts/login/`에서 최초 관리자로 로그인한다. `/admin/`이 열리고 왼쪽 메뉴에 **사용자와 권한**, **감사**, **설정**이 보여야 한다.
2. 관리 화면 **설정 > 보안**에서 2단계 인증 정책을 정한다.
3. 관리자 본인의 2단계 인증을 등록한다(포털 **보안**, `/portal/security/`).
4. `uv run manage.py pdf_sample`로 PDF 서비스를 점검한다.
5. 관리 화면 **감사 > 데이터 변경 기록**에 설치 작업이 `system:command:...`로 남았는지 확인한다.
6. `uv run manage.py check --deploy`로 운영 설정 경고가 없는지 확인한다.

## 6. 업데이트

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py migrate
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # 웹 워커를 새 코드로 다시 시작
sudo systemctl restart ninefruits-celery ninefruits-beat
```

Phase 1부터는 `migrate` 대신 `setup_install --force`(마이그레이션, 필수 데이터, 권한 동기화)를 실행한다. 서비스 이름은 설치 환경에 맞게 바꾼다.
