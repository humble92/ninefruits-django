# Ninefruits — 대학 학사 행정 시스템 (Django)

**언어 / Languages / 语言 / ພາສາ**

| 언어 | README | 매뉴얼 |
|---|---|---|
| 한국어 | [README.md](README.md) (이 문서) | [docs/manual/ko/](docs/manual/ko/README.md) |
| English | [README.en.md](README.en.md) | [docs/manual/en/](docs/manual/en/README.md) |
| 简体中文 | [README.zh_Hans.md](README.zh_Hans.md) | [docs/manual/zh_Hans/](docs/manual/zh_Hans/README.md) |
| ລາວ | [README.lo.md](README.lo.md) | [docs/manual/lo/](docs/manual/lo/README.md) |

Ninefruits는 여러 대학에 설치해 쓸 수 있는 학사 행정 시스템(Student Information System)입니다. 이 저장소는 [Ninefruits](https://github.com/humble92/ninefruits-laravel)(Laravel 13) v1.0.0의 기능 전체를 Python 3.14 / Django 6.1 / PostgreSQL 18로 옮기는 중입니다. 입학 지원부터 학적, 교육과정과 개설강좌, 수강신청, 성적, 강의평가, 증명서, 어학·종합시험, 출석, 졸업 사정, 보고서, LMS 연동 기반까지 다루며, 화면과 문서는 한국어·영어·중국어·라오스어를 지원합니다.

- 이식 계획: [porting/porting-plan.md](porting/porting-plan.md) (Phase 0~13)
- 이식 기록과 설계 결정: [porting/](porting/README.md)
- 이전 Django 프로토타입은 `legacy-playground` 브랜치에 있다. 참고용이며 이 구현의 기반이 아니다.

## 화면

- **관리 화면** `/admin/`: 교직원이 학적·교무·입학·증명서·시험·졸업·보고서를 처리합니다(Django admin + unfold). 메뉴와 버튼은 역할과 조직·과정 범위에 따른 권한으로 정해집니다.
- **포털** `/portal/`: 학생, 교수, 지원자가 쓰는 화면입니다(Django 템플릿 + HTMX + Alpine.js + Tailwind CSS). 메뉴는 사용자의 신분(학생, 교원, 지도교수 등)과 권한에 맞게 나옵니다.
- 두 화면은 같은 로그인(`/accounts/login/`, django-allauth)과 2단계 인증 정책을 씁니다.

## 기술 스택

Python 3.14, Django 6.1, django-unfold(관리 화면), HTMX 2·Alpine.js 3·Tailwind CSS 4·Vite(포털, django-vite), PostgreSQL 18(행 단위 보안, 트리거 감사), Redis·Celery·Flower(큐), Gotenberg(PDF), django-allauth(로그인·2단계 인증·SSO), Django REST framework(API). 의존성은 [uv](https://docs.astral.sh/uv/)(`uv.lock`)와 npm(`package-lock.json`)으로 고정합니다.

## 개발 환경 준비

### uv로 직접 실행

PostgreSQL 18, Redis 8, Gotenberg 8, Mailpit이 로컬에 있어야 합니다(없으면 아래 Docker Compose로 서비스만 띄웁니다: `docker compose up -d pgsql redis gotenberg mailpit`).

```bash
uv sync                                         # .venv, 개발 도구 포함
npm ci && npm run build                         # static/dist/ (또는 개발 중 `npm run dev` + VITE_DEV_MODE=true)
cp .env.example .env                            # 값 채우기: DJANGO_SECRET_KEY, PII 키(uv run manage.py pii_generate_key) 등
# DB 역할과 DB 준비(슈퍼유저 1회): docs/manual/ko/operations/installation.md 2절
uv run manage.py migrate                        # app_migrator 연결로 마이그레이션
uv run manage.py compilemessages --ignore=.venv
uv run manage.py security_sync_permissions
uv run manage.py security_create_administrator  # 최초 관리자 (createsuperuser는 비활성화)
uv run manage.py runserver
```

- 포털: http://localhost:8000/portal/ · 관리 화면: http://localhost:8000/admin/ (같은 로그인)
- 메일 확인(Mailpit): http://localhost:8025

### Docker Compose

호스트에는 Docker만 있으면 됩니다.

```bash
cp .env.example .env
docker compose up -d                            # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py migrate
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py security_sync_permissions
docker compose exec app uv run manage.py security_create_administrator
docker compose --profile vite up -d vite        # 선택: Vite 개발 서버(HMR), .env에 VITE_DEV_MODE=true
```

`pgsql` 컨테이너는 처음 시작할 때 DB 역할(`app_migrator`, `app_runtime`, `app_reporting`)을 만들고 개발 DB와 테스트 DB를 준비합니다(`docker/pgsql/`). 큐 모니터(Flower): http://localhost:5555

설치 절차 전체와 운영 환경은 [설치 매뉴얼](docs/manual/ko/operations/installation.md)을 보세요. 데모 데이터(`setup_demo`)와 데모 계정은 Phase 1에서 추가됩니다.

## 자주 쓰는 명령

| 명령 | 내용 |
|---|---|
| `uv run pytest -n auto -m "not concurrency"` | 테스트(동시성 테스트는 `-m concurrency`로 따로) |
| `uv run ruff format && uv run ruff check` | 코드 스타일, 정적 검사 |
| `uv run mypy ninefruits config` | 타입 검사 |
| `uv run tools/checks/raw_sql.py` | 원시 SQL 검사(문자열로 만든 SQL 금지) |
| `uv run manage.py naming_check` | 명명 검사(DB 테이블·컬럼, 마이그레이션, 명령, 번역) |
| `uv run manage.py i18n_missing --strict` | 번역 누락 확인 |
| `uv run manage.py migrate` | 마이그레이션(자동으로 `app_migrator` 연결 사용) |
| `uv run manage.py security_sync_permissions` | 코드의 권한 카탈로그를 DB에 반영 |
| `pre-commit install` | 커밋 전 ruff, mypy, 원시 SQL 검사 |

전체 목록은 [운영 명령 레퍼런스](docs/manual/ko/operations/commands.md)에 있습니다. CI(`.github/workflows/ci.yml`)는 품질 검사와 테스트 두 job으로 같은 검사를 실행합니다.

## 문서

- [매뉴얼](docs/manual/ko/README.md): 관리자 매뉴얼 28장, 운영 매뉴얼 9편
- [운영 매뉴얼](docs/manual/ko/README.md#운영-매뉴얼): [설치](docs/manual/ko/operations/installation.md), [운영 명령](docs/manual/ko/operations/commands.md), [보안 키](docs/manual/ko/operations/security-keys.md)
- [개발 규칙](docs/development/naming.md): [명명 규칙](docs/development/naming.md), [리뷰 체크리스트](docs/development/review-checklist.md)

## 라이선스

[MIT 라이선스](LICENSE). 누구나 자유롭게 사용·수정·배포할 수 있으며, 저작권 표시와 라이선스 문구를 함께 유지하면 됩니다.

---

**감사의 말**

이 시스템을 가능하게 한 YUSTIC(연변과기대 학사행정망 시스템)에 감사를 드립니다. YUSTIC은 수 명의 개발팀이 수 년 동안 함께 땀흘리며 꿈을 꾸고 수고로 이루어 낸 결과물입니다. 함께 했던 동료들에게 그리움과 존경과 감사의 말을 이 시스템개발로 대신합니다.
