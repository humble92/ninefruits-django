# Installation

- Audience: IT operators
- Related: [command reference](commands.md), [key management](security-keys.md), [deployment checklist](deployment-checklist.md)

## 1. Requirements

| Component | Version | Notes |
|---|---|---|
| Python | 3.14 | Installed and run with [uv](https://docs.astral.sh/uv/) (`uv sync`). System packages: `gettext` (compiling translations), `libmagic` (file type detection) |
| Node.js | 22 | Builds the screen assets (`npm ci && npm run build`). Production servers only need the build output |
| PostgreSQL | 18 | `btree_gist`, `pg_trgm` extensions (installed by the migrations), ICU collations |
| Redis | 8 | Cache, sessions, Celery broker and results |
| Gotenberg | 8 | PDF generation. Expose on the internal network only |
| Mail server | SMTP | Password resets, two-factor email codes, invitations, notifications |
| Web server | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`. Nginx serves `staticfiles/` itself and passes everything else to gunicorn |
| Queue worker | Celery worker | Keep `uv run celery -A config worker` running under a process manager (systemd, supervisor) |
| Scheduler | Celery beat | Run `uv run celery -A config beat` on **exactly one** machine (database scheduler, django-celery-beat) |
| Queue monitor | Flower (optional) | `uv run celery -A config flower`. Keep it on the internal network or behind an Nginx access restriction (or Flower's `--basic-auth`); never expose it |

## 2. Database preparation

Run once as the database superuser. The application never uses the superuser.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| Role | Environment variables | Purpose |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | Running the application (row level security applies, no DDL) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | Migrations, audit sealing and pruning only (`migrate` uses this connection automatically) |
| `app_reporting` | (configured in BI tools) | Reading the `reporting` schema |

In the Docker Compose development environment, `docker/pgsql/20-create-app-roles.sh` does the same when the `pgsql` container starts for the first time (roles, `ninefruits` and test databases).

## 3. Environment configuration

Copy `.env.example` to `.env` and fill in the values (in production, provide them as environment variables or from a secret store). Values that must change:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. Store it as described in [key management](security-keys.md).
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **If they are lost, encrypted personal data cannot be recovered.** Store them separately as described in [key management](security-keys.md).
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: the number of reverse proxies in front of the application (`1` for a single Nginx). See the [deployment checklist](deployment-checklist.md#proxies-and-the-client-address)
- `INSTITUTION_TIMEZONE`: default institution time zone for the first installation (for example `Asia/Seoul`)

The full list of production environment variables is in the [deployment checklist](deployment-checklist.md#environment-variables).

## 4. Installation

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` runs, in order: the migrations (over the `app_migrator` connection), essential data (role templates and permission sync, countries, languages, lookup types, org unit types, status change types, registration rule bundles), the institution defaults (default language, time zone, institution name), fixing the grade scale, installation profiles and the first administrator. In deployment scripts run it with `--force` and options; the administrator password is read from standard input.

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

Installation profiles (`--profile=`, may be given more than once)

| Key | Contents |
|---|---|
| `korean-university` | Spring/summer/fall/winter term types, the 4.5 grade scale, course categories, periods from 09:00, room types, admission types and application documents, the default course evaluation form, certificate kinds with templates in four languages |
| `yust-legacy` | Everything in `korean-university`, plus credit limits by admission year and for nursing, credit bank courses outside the limit, the 4.3 grade scale and its grading policy |

Without a profile, enter these in the admin panel. Applying a profile again later keeps the values administrators changed. The grade scale cannot change once set (grades and GPAs are stored on that scale).

Django's `createsuperuser` is disabled. The first administrator is created only with `setup_install` or `security_create_administrator` ([command reference](commands.md)).

After installation, the business administrators enter the reference data following [chapter 5 of the administrator manual, initial setup order](../admin/05-institution-setup.md). Register the server processes (gunicorn, Celery worker, beat) as described in the [deployment checklist](deployment-checklist.md) and [scheduled jobs](scheduled-jobs.md).

### Docker Compose (development)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| Service | Address |
|---|---|
| Application | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (development mailbox) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite dev server (optional, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

The production image is the `production` target of the `Dockerfile` (the default). It runs `compilemessages` and `collectstatic` at build time and starts gunicorn. The same image runs the worker and beat (`uv run --no-sync celery -A config worker|beat`).

## 5. Verifying the installation

1. Sign in as the first administrator at `/accounts/login/`. `/admin/` opens and the sidebar shows **Users and access**, **Audit** and **Settings**.
2. In the admin panel, set the two-factor policy under **Settings > Security**.
3. Enroll two-factor authentication for the administrator (portal **Security**, `/portal/security/`).
4. Check the PDF service with `uv run manage.py pdf_sample`.
5. In the admin panel, check that **Audit > Data changes** shows the installation as `system:command:setup_install`.
6. Check that `uv run manage.py check --deploy` reports no production warnings and that `GET /api/v1/health/` answers `{"status": "ok"}` (beat must have run for a minute).

## 6. Updates

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py setup_install --force      # migrations, essential data, permission sync
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # restart the web workers on the new code
sudo systemctl restart ninefruits-celery ninefruits-beat
```

Adjust the service names to your installation. Follow the [deployment checklist](deployment-checklist.md#deployment-procedure) for the backup and checks around an update.
