# 배포 체크리스트와 gunicorn·Python 설정

- 대상: IT 운영자
- 관련: [설치](installation.md), [키 관리](security-keys.md), [예약 작업](scheduled-jobs.md), [부하 테스트](load-testing.md)

## Python과 의존성

- **Python 3.14**의 최신 패치 릴리스를 쓴다. 컨테이너·서버 이미지를 만들 때 Python 패치 버전을 고정하지 말고 새로 받는다(`Dockerfile`의 `python:3.14-slim`).
- 파이썬 의존성은 `uv.lock`으로 고정되어 있다. 운영 설치는 항상 `uv sync --frozen --no-dev`로 한다(잠금 파일과 다르면 실패한다). 개발 도구(pytest, ruff, mypy, Playwright)는 운영 환경에 들어가지 않는다.
- Django 보안 릴리스가 나오면 `uv lock --upgrade-package django`로 올리고 테스트 뒤 배포한다. 의존성 취약점은 CI와 같이 `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`로 확인한다.
- `uv run manage.py check --deploy`는 운영 설정(`DEBUG`, HTTPS, 쿠키, HSTS, 비밀 키 길이)의 경고를 보여 준다. 배포할 때마다 경고 0건이어야 한다.

## gunicorn과 Nginx

| 항목 | 값 | 이유 |
|---|---|---|
| gunicorn 실행 | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, sync 워커. 워커 수와 연결 풀 크기는 환경 변수로 정하고 근거는 [부하 테스트](load-testing.md)에 있다 |
| gunicorn 바인드 | `127.0.0.1:8000` 또는 유닉스 소켓 | gunicorn을 외부에 직접 노출하지 않는다. 항상 Nginx 뒤에 둔다 |
| 워커 재시작 | 배포 시 `HUP`(systemd `reload`) | 진행 중인 요청을 마치고 새 코드로 워커를 바꾼다 |
| DB 연결 | `DB_POOL=true`이면 워커마다 psycopg 연결 풀(`DB_POOL_MIN`, `DB_POOL_MAX`) | 워커 수 × `DB_POOL_MAX` + Celery 연결이 PostgreSQL `max_connections`보다 작아야 한다. 풀에 돌아가는 연결은 DB 세션 수행자를 지운다(`ninefruits.core.pool.reset_connection`) |
| Nginx `client_max_body_size` | `32m` | 입학 서류·시험 증빙·사진 업로드 상한(앱 검증 5MB·2MB보다 여유) |
| Nginx 정적 파일 | `location /static/ { alias <저장소>/staticfiles/; }` | `collectstatic` 결과를 Nginx가 직접 제공한다 |
| 비공개 파일 | `PRIVATE_MEDIA_ROOT`(기본 `storage/private`)를 Nginx에 **연결하지 않는다** | 사진, 지원 서류, 증명서 PDF는 권한을 확인하는 화면으로만 내려받는다 |
| Nginx 헤더 | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, 선택: `X-Request-Id $request_id` | 클라이언트 주소, HTTPS 판단, 요청 단위 추적 |
| Gotenberg, Redis, PostgreSQL | 내부망 주소만 | 외부에 노출하지 않는다 |

```nginx
server {
    listen 443 ssl;
    server_name sis.example.ac.kr;
    client_max_body_size 32m;

    location /static/ { alias /srv/ninefruits/staticfiles/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-Id $request_id;
    }
}
```

### 프록시와 클라이언트 주소

로그인 제한, API 요청 제한, 감사 기록의 IP 주소는 `ninefruits.core.http.client_ip`가 정한 클라이언트 주소를 쓴다.

- `TRUSTED_PROXY_COUNT`: 애플리케이션 앞에서 `X-Forwarded-For`에 주소를 덧붙이는 리버스 프록시 수. Nginx 하나면 `1`, 로드 밸런서 + Nginx면 `2`. `0`(기본)이면 `REMOTE_ADDR`를 쓴다. 오른쪽에서 이 수만큼 센 항목이 클라이언트 주소이고, 그보다 왼쪽 항목(클라이언트가 보낸 값)은 믿지 않는다.
- **값이 실제 프록시 수보다 작으면** 모든 사용자가 Nginx 주소 하나로 보여 로그인 제한이 학교 전체에 걸린다. **크면** 클라이언트가 보낸 `X-Forwarded-For`를 믿게 되어 제한을 우회할 수 있다. 배포 후 관리 화면 **감사 > 보안 이벤트**의 IP 주소가 실제 사용자 주소인지 확인한다.
- `LOGIN_RATE_LIMIT_PER_IP`: 클라이언트 주소당 로그인 시도 수(django-allauth, 기본 `30/m/ip`). 원본에는 없던 제한이다. 캠퍼스 전체가 NAT 주소 하나로 나가면 수강신청 첫날 아침에 부족하므로 늘린다(예: `300/m/ip`). 비우면 주소당 제한이 없다(원본과 같다). 계정별 실패 제한(1분 5회)과 계정 잠금은 이 값과 관계없이 동작한다.

## 환경 변수

`.env.example`이 개발 기본값이다. 운영에서는 비밀 값을 비밀 저장소에서 넣는다.

| 변수 | 운영 값 | 비고 |
|---|---|---|
| `DJANGO_ENV` | `production` | `setup_demo`를 거부하고 관리 화면의 환경 표시(배지)를 없앤다 |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, 보안 쿠키 |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | 비밀 저장소 | [키 관리](security-keys.md). 교체 시 이전 키는 `DJANGO_SECRET_KEY_FALLBACKS` |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | 쉼표 목록 |
| `APP_URL` | `https://sis.example.ac.kr` | 메일 링크, 증명서 진위 확인 QR |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | 비밀 저장소 | 잃으면 개인정보 복호화 불가 |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | 애플리케이션, Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | `migrate`·`setup_install`·`audit_seal`·`audit_prune`이 쓴다. 비밀번호는 배포를 실행하는 서버와 감사 봉인(`audit_seal`)을 실행하는 서버에만 둔다 |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, [부하 테스트](load-testing.md) 결정값, `60`, `2000`, `127.0.0.1` | `config/gunicorn.py`가 읽는다. 기본 워커 수는 CPU 코어당 2 + 1. `GUNICORN_FORWARDED_ALLOW_IPS`는 gunicorn이 믿는 `X-Forwarded-Proto`의 출처일 뿐이고 클라이언트 주소는 `TRUSTED_PROXY_COUNT`가 정한다 |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | [부하 테스트](load-testing.md) 결정값: `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD`는 준비된 문장을 켠다(RLS 쿼리 계획 비용 절감). 0이면 끔 |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | 내부망 Redis | 브로커와 결과는 기본으로 `REDIS_URL` |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION`(`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | 학교 SMTP 중계 | 초대, 2단계 인증 코드, 수강·성적 알림 |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | 내부망 주소, `60` | |
| `PRIVATE_MEDIA_ROOT` | 백업되는 디스크 | 비공개 파일 저장소 |
| `TRUSTED_PROXY_COUNT` | 보통 `1` | 위 절 |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` 또는 더 크게 | 위 절 |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | 처음 HTTPS를 켤 때는 HSTS를 짧게(`300`) 시험한 뒤 늘린다 |
| `SESSION_LIFETIME_MINUTES` | `120` | 로그인 세션 수명 |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, 기관 시간대 | 서버 시각과 예약 작업은 UTC, 화면 표시는 기관 시간대 |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | 기본값 | [LMS 연동 가이드](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | 로그는 표준 출력에 JSON 한 줄씩 |
| `VITE_DEV_MODE` | `false` | 운영은 빌드 결과(`static/dist/manifest.json`)를 쓴다 |

## 배포 절차

1. 백업([백업과 복구](backup-restore.md)), 그리고 `uv run manage.py audit_verify_chain`.
2. 코드 배포: `git pull`(또는 새 이미지), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force`: 마이그레이션(`app_migrator` 연결로 자동 전환), 필수 데이터 갱신(관리자 수정 유지), 권한 카탈로그 동기화. 마이그레이션만 따로 돌릴 때도 `uv run manage.py migrate`는 자동으로 `app_migrator`를 쓴다. `app_runtime`으로 DDL을 실행하는 방법은 없다.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. 운영 Docker 이미지는 빌드할 때 두 명령을 실행한다.
5. 프로세스 재시작: gunicorn `reload`(HUP), Celery worker 재시작(TERM으로 진행 중 작업을 마친 뒤 종료, `acks_late`라 중단된 작업은 다시 실행된다), Celery beat 재시작. **beat는 전체에서 한 프로세스만** 실행한다. 두 대가 돌면 예약 작업이 두 번 큐에 들어간다(각 작업의 Redis 잠금이 동시 실행은 막지만 중복 큐잉은 막지 못한다).
6. 확인: `uv run manage.py check --deploy`, `uv run manage.py system_health_check`(종료 코드 0), `GET /api/v1/health/`(`ok`), 관리 화면 로그인, `uv run manage.py pdf_sample`. Flower에서 worker가 붙었는지 본다.

## 정기 점검

| 주기 | 할 일 |
|---|---|
| 매일(자동) | `audit.seal`, `lms.reconcile`, 수강 예약 좌석 해제, 대기자 승격, 지원서 초안 만료([예약 작업](scheduled-jobs.md)) |
| 매주 | `/api/v1/health/`와 `check --deploy`, Python·OS·의존성 보안 업데이트(`pip-audit`) 확인, Flower의 실패 작업 확인 |
| 매월 | `media_prune_orphans --dry-run`, 백업 복구 연습, `audit_verify_chain` |
| 학기마다 | 역할 할당 점검(퇴직·이동자), 보존 기간 지난 감사 정리(`audit_prune`), 수강신청 전 `LOGIN_RATE_LIMIT_PER_IP`와 워커 수 재확인 |
