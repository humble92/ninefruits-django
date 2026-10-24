# Ninefruits — Student Information System (Django)

**언어 / Languages / 语言 / ພາສາ**

| Language | README | Manual |
|---|---|---|
| 한국어 | [README.md](README.md) | [docs/manual/ko/](docs/manual/ko/README.md) |
| English | [README.en.md](README.en.md) (this file) | [docs/manual/en/](docs/manual/en/README.md) |
| 简体中文 | [README.zh_Hans.md](README.zh_Hans.md) | [docs/manual/zh_Hans/](docs/manual/zh_Hans/README.md) |
| ລາວ | [README.lo.md](README.lo.md) | [docs/manual/lo/](docs/manual/lo/README.md) |

Ninefruits is a student information system that any university can install. This repository is porting every feature of [Ninefruits](https://github.com/humble92/ninefruits-laravel) (Laravel 13) v1.0.0 to Python 3.14 / Django 6.1 / PostgreSQL 18. It covers admissions, student records, curriculum and sections, registration, grades, course evaluation, certificates, language and comprehensive examinations, attendance, degree audits, reports and an LMS integration base, with screens and documents in Korean, English, Simplified Chinese and Lao.

- Porting plan: [porting/porting-plan.md](porting/porting-plan.md) (Phases 0 to 13, in Korean)
- Porting records and design decisions: [porting/](porting/README.md)
- The earlier Django prototype is on the `legacy-playground` branch, for reference only.

## Screens

- **Administration panel** `/admin/`: staff handle student records, academic affairs, admissions, certificates, examinations, graduation and reports (Django admin + unfold). Menus and buttons follow the permissions granted by roles and their org unit or program scope.
- **Portal** `/portal/`: the screens for students, instructors and applicants (Django templates + HTMX + Alpine.js + Tailwind CSS). The menu matches the user's personas (student, instructor, advisor, ...) and permissions.
- Both use the same sign-in (`/accounts/login/`, django-allauth) and the same two-factor policy.

## Technology

Python 3.14, Django 6.1, django-unfold (administration panel), HTMX 2, Alpine.js 3, Tailwind CSS 4 and Vite (portal, django-vite), PostgreSQL 18 (row level security, trigger audit), Redis, Celery and Flower (queues), Gotenberg (PDF), django-allauth (sign-in, two-factor authentication, SSO), Django REST framework (API). Dependencies are pinned with [uv](https://docs.astral.sh/uv/) (`uv.lock`) and npm (`package-lock.json`).

## Development setup

### Running with uv

PostgreSQL 18, Redis 8, Gotenberg 8 and Mailpit must be available locally (or start just the services with Docker Compose: `docker compose up -d pgsql redis gotenberg mailpit`).

```bash
uv sync                                         # .venv including the development tools
npm ci && npm run build                         # static/dist/ (or `npm run dev` + VITE_DEV_MODE=true while developing)
cp .env.example .env                            # fill in DJANGO_SECRET_KEY, PII keys (uv run manage.py pii_generate_key), ...
# Database roles and database (once, as superuser): docs/manual/en/operations/installation.md section 2
uv run manage.py migrate                        # migrations over the app_migrator connection
uv run manage.py compilemessages --ignore=.venv
uv run manage.py security_sync_permissions
uv run manage.py security_create_administrator  # first administrator (createsuperuser is disabled)
uv run manage.py runserver
```

- Portal: http://localhost:8000/portal/ · Administration panel: http://localhost:8000/admin/ (same sign-in)
- Mail (Mailpit): http://localhost:8025

### Docker Compose

Only Docker is needed on the host.

```bash
cp .env.example .env
docker compose up -d                            # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py migrate
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py security_sync_permissions
docker compose exec app uv run manage.py security_create_administrator
docker compose --profile vite up -d vite        # optional: Vite dev server (HMR), VITE_DEV_MODE=true in .env
```

On its first start the `pgsql` container creates the database roles (`app_migrator`, `app_runtime`, `app_reporting`) and prepares the development and test databases (`docker/pgsql/`). Queue monitor (Flower): http://localhost:5555

See the [installation manual](docs/manual/en/operations/installation.md) for the full procedure and production. Demo data (`setup_demo`) and demo accounts arrive in Phase 1.

## Common commands

| Command | Purpose |
|---|---|
| `uv run pytest -n auto -m "not concurrency"` | Tests (concurrency tests separately with `-m concurrency`) |
| `uv run ruff format && uv run ruff check` | Code style and linting |
| `uv run mypy ninefruits config` | Type checking |
| `uv run tools/checks/raw_sql.py` | Raw SQL check (no SQL built from strings) |
| `uv run manage.py naming_check` | Naming check (database tables and columns, migrations, commands, translations) |
| `uv run manage.py i18n_missing --strict` | Missing translations |
| `uv run manage.py migrate` | Migrations (uses the `app_migrator` connection automatically) |
| `uv run manage.py security_sync_permissions` | Brings the permission catalog in the code into the database |
| `pre-commit install` | ruff, mypy and the raw SQL check before each commit |

The full list is in the [command reference](docs/manual/en/operations/commands.md). CI (`.github/workflows/ci.yml`) runs the same checks in two jobs, quality and tests.

## Documentation

- [Manual](docs/manual/en/README.md): administrator manual (28 chapters), operations manual (9 documents)
- Operations: [installation](docs/manual/en/operations/installation.md), [commands](docs/manual/en/operations/commands.md), [security keys](docs/manual/en/operations/security-keys.md)
- Development rules (Korean): [naming conventions](docs/development/naming.md), [review checklist](docs/development/review-checklist.md)

## License

[MIT License](LICENSE). Anyone may use, modify and distribute it freely, as long as the copyright notice and license text are kept.

---

**Acknowledgement**

Our thanks go to YUSTIC, the academic administration system of Yanbian University of Science and Technology, which made this system possible. YUSTIC was the work of a small team of developers who dreamed, sweated and built together over many years. This system is our way of saying how much we miss, respect and thank the colleagues we worked with.
