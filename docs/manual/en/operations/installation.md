# Installation

- Audience: IT operators
- Related: [command reference](commands.md), [key management](security-keys.md)

## 1. Requirements

| Component | Version | Notes |
|---|---|---|
| Python | 3.14 | Installed and run with [uv](https://docs.astral.sh/uv/) (`uv sync`). System packages: `gettext` (compiling translations), `libmagic` (file type detection) |
| Node.js | 22 | Builds the screen assets (`npm ci && npm run build`). Production servers only need the build output |
| PostgreSQL | 18 | `btree_gist`, `pg_trgm` extensions (installed by the migrations), ICU collations |
| Redis | 8 | Cache, Celery broker and results |
| Gotenberg | 8 | PDF generation. Expose on the internal network only |
| Mail server | SMTP | Password resets, two-factor email codes |
| Web server | gunicorn + Nginx | `uv run gunicorn config.wsgi`. Nginx serves `staticfiles/` itself and passes everything else to gunicorn |
| Queue worker | Celery worker | Keep `uv run celery -A config worker` running under a process manager (systemd, supervisor) |
| Scheduler | Celery beat | Run `uv run celery -A config beat` on exactly one machine (database scheduler, django-celery-beat) |
| Queue monitor | Flower (optional) | `uv run celery -A config flower`. Put it behind Nginx so only users with `View the queue monitor` reach it |

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
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | Migrations only (`migrate` uses this connection automatically) |
| `app_reporting` | (configured in BI tools) | Reading the `reporting` schema |

In the Docker Compose development environment, `docker/pgsql/20-create-app-roles.sh` does the same when the `pgsql` container starts for the first time (roles, `ninefruits` and test databases).

## 3. Environment configuration

Copy `.env.example` to `.env` and fill in the values (in production, provide them as environment variables or from a secret store). Values that must change:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. Store it as described in [key management](security-keys.md).
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **If they are lost, encrypted personal data cannot be recovered.** Store them separately as described in [key management](security-keys.md).
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `INSTITUTION_TIMEZONE`: default institution time zone for the first installation (for example `Asia/Seoul`)

## 4. Installation

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py migrate                    # schema and data migrations over the app_migrator connection
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py security_sync_permissions  # brings the permission catalog into the database
echo "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator \
    --email=admin@example.ac.kr --name="Administrator" --password-stdin
```

Django's `createsuperuser` is disabled. The first administrator is created only with `security_create_administrator` ([command reference](commands.md)). The command needs the system administrator role (essential data) and says what to run first when it is missing. From Phase 1 on, `setup_install` runs the migrations, essential data, institution defaults, installation profiles and the first administrator in order.

After installation, the business administrators enter the reference data following [chapter 5 of the administrator manual, initial setup order](../admin/05-institution-setup.md).

### Docker Compose (development)

```bash
cp .env.example .env
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py migrate
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py security_sync_permissions
docker compose exec app uv run manage.py security_create_administrator --email=admin@example.test --name="Administrator"
```

| Service | Address |
|---|---|
| Application | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (development mailbox) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite dev server (optional, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

## 5. Verifying the installation

1. Sign in as the first administrator at `/accounts/login/`. `/admin/` must open, with **Users and access**, **Audit** and **Settings** in the menu on the left.
2. Set the two-factor policy under **Settings > Security** in the administration panel.
3. Enroll the administrator's own two-factor authentication (portal **Security**, `/portal/security/`).
4. Check the PDF service with `uv run manage.py pdf_sample`.
5. Check that the installation steps appear as `system:command:...` under **Audit > Data changes** in the administration panel.
6. Check that `uv run manage.py check --deploy` reports no production setting warnings.

## 6. Updates

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py migrate
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # restart the web workers on the new code
sudo systemctl restart ninefruits-celery ninefruits-beat
```

From Phase 1 on, run `setup_install --force` (migrations, essential data, permission sync) instead of `migrate`. Adjust the service names to your installation.
