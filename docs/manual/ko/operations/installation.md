# 설치

- 대상: IT 운영자
- 관련: [명령 레퍼런스](commands.md), [키 관리](security-keys.md), [배포 체크리스트](deployment-checklist.md)

## 1. 요구 사항

| 구성 요소 | 버전 | 비고 |
|---|---|---|
| Python | 3.14 | [uv](https://docs.astral.sh/uv/)로 설치·실행한다(`uv sync`). 시스템 패키지: `gettext`(번역 컴파일), `libmagic`(파일 형식 판별) |
| Node.js | 22 | 화면 자산 빌드(`npm ci && npm run build`). 운영 서버에는 빌드 결과만 있으면 된다 |
| PostgreSQL | 18 | `btree_gist`, `pg_trgm` 확장(마이그레이션이 설치), ICU collation |
| Redis | 8 | 캐시, 세션, Celery 브로커와 결과 |
| Gotenberg | 8 | PDF 생성. 내부망에만 노출 |
| 메일 서버 | SMTP | 비밀번호 재설정, 2단계 인증 이메일 코드, 초대, 알림 |
| 웹 서버 | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`. Nginx는 `staticfiles/`를 직접 제공하고 나머지를 gunicorn으로 넘긴다 |
| 큐 워커 | Celery worker | `uv run celery -A config worker`를 프로세스 관리자(systemd, supervisor)로 상시 실행 |
| 스케줄러 | Celery beat | `uv run celery -A config beat`를 **한 대에서만** 실행(DB 스케줄러, django-celery-beat) |
| 큐 모니터 | Flower (선택) | `uv run celery -A config flower`. 내부망이나 Nginx 접근 제한(또는 Flower `--basic-auth`) 뒤에 두고 외부에 노출하지 않는다 |

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
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | 마이그레이션, 감사 봉인·정리만(`migrate`가 자동으로 이 연결을 쓴다) |
| `app_reporting` | (BI 도구에 설정) | `reporting` 스키마 조회 |

Docker Compose 개발 환경에서는 `pgsql` 컨테이너가 처음 시작할 때 `docker/pgsql/20-create-app-roles.sh`가 같은 일을 한다(역할 생성, `ninefruits`와 테스트 DB 준비).

## 3. 환경 설정

`.env.example`을 `.env`로 복사해 값을 채운다(운영에서는 환경 변수나 비밀 저장소로 넣는다). 반드시 바꿀 값

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. [키 관리](security-keys.md)에 따라 보관한다.
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **분실하면 암호화된 개인정보를 복구할 수 없다.** [키 관리](security-keys.md)에 따라 별도 보관한다.
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: 앞단 리버스 프록시 수(Nginx 하나면 `1`). [배포 체크리스트](deployment-checklist.md#프록시와-클라이언트-주소)
- `INSTITUTION_TIMEZONE`: 최초 설치 시 기관 시간대 기본값(예: `Asia/Seoul`)

운영 환경 변수 전체 목록은 [배포 체크리스트](deployment-checklist.md#환경-변수)에 있다.

## 4. 설치

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # 질문에 답하며 진행
```

`setup_install`은 마이그레이션(`app_migrator` 연결), 필수 데이터(역할 템플릿과 권한 동기화, 국가, 언어, 코드 목록 유형, 조직 단위 유형, 학적 변동 유형, 수강 규칙 묶음), 기관 기본 설정(기본 언어, 시간대, 기관 이름), 성적 척도 고정, 설치 프로파일, 최초 관리자를 차례로 처리한다. 배포 스크립트에서는 `--force`와 옵션으로 실행한다. 관리자 비밀번호는 표준 입력으로 받는다.

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
    --institution-name="한국대학교" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="관리자"
```

설치 프로파일(`--profile=`, 여러 번 지정 가능)

| 키 | 내용 |
|---|---|
| `korean-university` | 1학기/여름 계절/2학기/겨울 계절 학기 유형, 4.5 성적 척도, 교과 구분, 09:00부터 교시, 강의실 용도, 입학 구분과 지원 서류, 강의평가 기본 양식, 증명서 종류와 4개 언어 서식 |
| `yust-legacy` | `korean-university`에 더해 입학 연도·간호학과별 학점 상한, 학점 상한 밖 학점은행 과목, 4.3 성적 척도와 성적 처리 정책 |

적용하지 않으면 관리 화면에서 직접 입력한다. 나중에 다시 적용해도 관리자가 바꾼 값은 유지된다. 성적 척도는 한 번 정하면 바꿀 수 없다(성적과 평점이 그 척도로 저장된다).

Django `createsuperuser`는 비활성화되어 있다. 최초 관리자는 `setup_install`이나 `security_create_administrator`로만 만든다([명령 레퍼런스](commands.md)).

설치 후 업무 관리자는 [관리자 매뉴얼 5장 초기 세팅 순서](../admin/05-institution-setup.md)에 따라 기준정보를 입력한다. 운영 서버의 프로세스(gunicorn, Celery worker, beat)는 [배포 체크리스트](deployment-checklist.md)와 [예약 작업](scheduled-jobs.md)에 따라 등록한다.

### Docker Compose (개발)

```bash
cp .env.example .env                        # PII 키는 아래 명령 출력으로 채운다
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # 선택: 데모 데이터
```

| 서비스 | 주소 |
|---|---|
| 애플리케이션 | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit(개발용 메일함) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite 개발 서버(선택, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

운영 이미지는 `Dockerfile`의 `production` 대상(기본)이다. 빌드할 때 `compilemessages`와 `collectstatic`을 실행하고 gunicorn으로 시작한다. 같은 이미지로 worker와 beat(`uv run --no-sync celery -A config worker|beat`)를 띄운다.

## 5. 설치 확인

1. `/accounts/login/`에서 최초 관리자로 로그인한다. `/admin/`이 열리고 왼쪽 메뉴에 **사용자와 권한**, **감사**, **설정**이 보여야 한다.
2. 관리 화면 **설정 > 보안**에서 2단계 인증 정책을 정한다.
3. 관리자 본인의 2단계 인증을 등록한다(포털 **보안**, `/portal/security/`).
4. `uv run manage.py pdf_sample`로 PDF 서비스를 점검한다.
5. 관리 화면 **감사 > 데이터 변경 기록**에 설치 작업이 `system:command:setup_install`로 남았는지 확인한다.
6. `uv run manage.py check --deploy`로 운영 설정 경고가 없는지, `GET /api/v1/health/`가 `{"status": "ok"}`인지 확인한다(beat가 1분 넘게 돌아야 `ok`).

## 6. 업데이트

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py setup_install --force      # 마이그레이션, 필수 데이터, 권한 동기화
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # 웹 워커를 새 코드로 다시 시작
sudo systemctl restart ninefruits-celery ninefruits-beat
```

서비스 이름은 설치 환경에 맞게 바꾼다. 업데이트 전 백업과 확인 절차는 [배포 체크리스트](deployment-checklist.md#배포-절차)를 따른다.
