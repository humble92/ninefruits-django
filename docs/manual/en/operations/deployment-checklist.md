# Deployment checklist and gunicorn and Python settings

- Audience: IT operators
- Related: [installation](installation.md), [key management](security-keys.md), [scheduled jobs](scheduled-jobs.md), [load testing](load-testing.md)

## Python and dependencies

- Use the latest patch release of **Python 3.14**. When building container or server images, do not pin the Python patch version; take the latest (`python:3.14-slim` in the `Dockerfile`).
- Python dependencies are locked in `uv.lock`. Production installs always use `uv sync --frozen --no-dev` (it fails if the lock file disagrees). Development tools (pytest, ruff, mypy, Playwright) never reach production.
- When Django publishes a security release, upgrade with `uv lock --upgrade-package django`, run the tests and deploy. Check dependency vulnerabilities as CI does: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`.
- `uv run manage.py check --deploy` warns about production settings (`DEBUG`, HTTPS, cookies, HSTS, secret key length). Every deployment must have zero warnings.

## gunicorn and Nginx

| Item | Value | Reason |
|---|---|---|
| Running gunicorn | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, sync workers. The worker count and the connection pool size come from environment variables; the reasoning is in [load testing](load-testing.md) |
| gunicorn bind | `127.0.0.1:8000` or a Unix socket | Never expose gunicorn directly; always put it behind Nginx |
| Worker restart | `HUP` on deploy (systemd `reload`) | Finishes requests in progress and replaces the workers with the new code |
| DB connections | With `DB_POOL=true`, a psycopg connection pool per worker (`DB_POOL_MIN`, `DB_POOL_MAX`) | Workers × `DB_POOL_MAX` + Celery connections must stay below PostgreSQL's `max_connections`. A connection returned to the pool has its DB session actor cleared (`ninefruits.core.pool.reset_connection`) |
| Nginx `client_max_body_size` | `32m` | Upper limit for admission documents, examination evidence and photo uploads (headroom above the application's 5MB and 2MB validation) |
| Nginx static files | `location /static/ { alias <repository>/staticfiles/; }` | Nginx serves the `collectstatic` output itself |
| Private files | **Never map** `PRIVATE_MEDIA_ROOT` (default `storage/private`) in Nginx | Photos, application documents and certificate PDFs are downloaded only through permission checked views |
| Nginx headers | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, optionally `X-Request-Id $request_id` | Client address, HTTPS detection, per-request tracing |
| Gotenberg, Redis, PostgreSQL | Internal addresses only | Never exposed externally |

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

### Proxies and the client address

Sign-in limits, API rate limits and the IP addresses in the audit records use the client address determined by `ninefruits.core.http.client_ip`.

- `TRUSTED_PROXY_COUNT`: the number of reverse proxies in front of the application that append to `X-Forwarded-For`. `1` for a single Nginx, `2` for a load balancer plus Nginx. `0` (the default) uses `REMOTE_ADDR`. The entry this many places from the right is the client address; entries further left (sent by the client) are never trusted.
- **If the value is lower than the real number of proxies**, every user appears to come from the Nginx address and the sign-in limit applies to the whole campus at once. **If it is higher**, the application trusts an `X-Forwarded-For` sent by the client, and the limits can be bypassed. After deploying, check that the IP addresses under **Audit > Security events** in the admin panel are real user addresses.
- `LOGIN_RATE_LIMIT_PER_IP`: sign-in attempts per client address (django-allauth, default `30/m/ip`). The original had no such limit. If the whole campus leaves through one NAT address, this is too low for the first registration morning; raise it (for example `300/m/ip`). Empty means no per-address limit (as in the original). The per-account failure limit (5 a minute) and account lockout apply regardless of this value.

## Environment variables

`.env.example` holds development defaults. In production, inject secrets from the secret store.

| Variable | Production value | Notes |
|---|---|---|
| `DJANGO_ENV` | `production` | Refuses `setup_demo` and removes the environment badge from the admin panel |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, secure cookies |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | Secret store | [Key management](security-keys.md). When rotating, previous keys go to `DJANGO_SECRET_KEY_FALLBACKS` |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | Comma separated lists |
| `APP_URL` | `https://sis.example.ac.kr` | Links in mail, certificate verification QR codes |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | Secret store | If lost, personal data cannot be decrypted |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | Application and Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | Used by `migrate`, `setup_install`, `audit_seal` and `audit_prune`. Keep the password only on the server that runs deployments and the one that runs audit sealing (`audit_seal`) |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, the value from [load testing](load-testing.md), `60`, `2000`, `127.0.0.1` | Read by `config/gunicorn.py`. The default worker count is 2 per CPU core + 1. `GUNICORN_FORWARDED_ALLOW_IPS` only says whose `X-Forwarded-Proto` gunicorn trusts; the client address comes from `TRUSTED_PROXY_COUNT` |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | Values decided in [load testing](load-testing.md): `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` turns on prepared statements (cuts RLS query planning cost); 0 turns them off |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Internal Redis | Broker and results default to `REDIS_URL` |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | The university's SMTP relay | Invitations, two-factor codes, registration and grade notifications |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | Internal address, `60` | |
| `PRIVATE_MEDIA_ROOT` | A disk that is backed up | Private file storage |
| `TRUSTED_PROXY_COUNT` | Usually `1` | Section above |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` or higher | Section above |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | When first enabling HTTPS, try a short HSTS (`300`) before raising it |
| `SESSION_LIFETIME_MINUTES` | `120` | Lifetime of a signed-in session |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, the institution's time zone | Server times and scheduled jobs in UTC, screens in the institution's time zone |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | Defaults | [LMS integration guide](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | Logs go to standard output as one JSON object per line |
| `VITE_DEV_MODE` | `false` | Production uses the build output (`static/dist/manifest.json`) |

## Deployment procedure

1. Back up ([backup and restore](backup-restore.md)) and run `uv run manage.py audit_verify_chain`.
2. Deploy the code: `git pull` (or a new image), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force`: migrations (switching to the `app_migrator` connection automatically), refreshed essential data (administrator edits are kept), permission catalog sync. When running migrations on their own, `uv run manage.py migrate` also uses `app_migrator` automatically. There is no way to run DDL as `app_runtime`.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. The production Docker image runs both at build time.
5. Restart the processes: gunicorn `reload` (HUP), the Celery worker (TERM lets running tasks finish; with `acks_late`, an interrupted task runs again), Celery beat. Run **exactly one beat process** across all servers. With two, every scheduled job is queued twice (each job's Redis lock prevents simultaneous runs, not duplicate queueing).
6. Verify: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (exit code 0), `GET /api/v1/health/` (`ok`), signing in to the admin panel, `uv run manage.py pdf_sample`. Check in Flower that the worker is connected.

## Routine checks

| Frequency | Task |
|---|---|
| Daily (automatic) | `audit.seal`, `lms.reconcile`, release of reserved registration seats, waitlist promotion, expiry of application drafts ([scheduled jobs](scheduled-jobs.md)) |
| Weekly | `/api/v1/health/` and `check --deploy`, Python, OS and dependency security updates (`pip-audit`), failed tasks in Flower |
| Monthly | `media_prune_orphans --dry-run`, backup restore drill, `audit_verify_chain` |
| Every term | Review role assignments (people who left or moved), prune audit records past their retention period (`audit_prune`), before registration re-check `LOGIN_RATE_LIMIT_PER_IP` and the worker count |
