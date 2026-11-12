# Pag-install

- Para kanino: mga IT operator
- Kaugnay: [sanggunian ng mga command](commands.md), [pamamahala ng key](security-keys.md), [checklist sa deployment](deployment-checklist.md)

## 1. Mga kinakailangan

| Component | Bersiyon | Mga tala |
|---|---|---|
| Python | 3.14 | Ini-install at pinatatakbo gamit ang [uv](https://docs.astral.sh/uv/) (`uv sync`). Mga system package: `gettext` (pag-compile ng mga salin), `libmagic` (pagtukoy sa uri ng file) |
| Node.js | 22 | Binubuo ang mga asset ng screen (`npm ci && npm run build`). Ang build output lamang ang kailangan ng mga production server |
| PostgreSQL | 18 | Mga extension na `btree_gist`, `pg_trgm` (ini-install ng mga migration), mga ICU collation |
| Redis | 8 | Cache, mga session, broker at mga resulta ng Celery |
| Gotenberg | 8 | Paggawa ng PDF. Ilantad sa panloob na network lamang |
| Mail server | SMTP | Pag-reset ng password, mga code ng two-factor sa email, mga imbitasyon, mga abiso |
| Web server | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`. Ang Nginx mismo ang naghahatid ng `staticfiles/` at ipinapasa ang lahat ng iba pa sa gunicorn |
| Queue worker | Celery worker | Panatilihing tumatakbo ang `uv run celery -A config worker` sa ilalim ng process manager (systemd, supervisor) |
| Scheduler | Celery beat | Patakbuhin ang `uv run celery -A config beat` sa **eksaktong isang** machine (database scheduler, django-celery-beat) |
| Queue monitor | Flower (opsiyonal) | `uv run celery -A config flower`. Panatilihin ito sa panloob na network o sa likod ng paghihigpit sa access ng Nginx (o ng `--basic-auth` ng Flower); huwag kailanman ilantad |

## 2. Paghahanda ng database

Patakbuhin nang isang beses bilang superuser ng database. Hindi kailanman ginagamit ng application ang superuser.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| Role | Mga environment variable | Layunin |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | Pagpapatakbo ng application (ipinatutupad ang row level security, walang DDL) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | Mga migration, pag-seal at pruning ng audit lamang (awtomatikong ginagamit ng `migrate` ang koneksiyong ito) |
| `app_reporting` | (itinatakda sa mga BI tool) | Pagbasa sa schema na `reporting` |

Sa development environment na Docker Compose, ganito rin ang ginagawa ng `docker/pgsql/20-create-app-roles.sh` kapag unang nagsimula ang container na `pgsql` (mga role, ang `ninefruits` at mga test database).

## 3. Configuration ng environment

Kopyahin ang `.env.example` sa `.env` at punan ang mga value (sa production, ibigay ang mga ito bilang mga environment variable o mula sa isang secret store). Mga value na dapat baguhin:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. Iimbak ito gaya ng inilalarawan sa [pamamahala ng key](security-keys.md).
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **Kapag nawala ang mga ito, hindi na mababawi ang naka-encrypt na personal na datos.** Iimbak nang hiwalay gaya ng inilalarawan sa [pamamahala ng key](security-keys.md).
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: ang bilang ng mga reverse proxy sa harap ng application (`1` para sa iisang Nginx). Tingnan ang [checklist sa deployment](deployment-checklist.md#mga-proxy-at-ang-address-ng-client)
- `INSTITUTION_TIMEZONE`: default na time zone ng institusyon para sa unang pag-install (halimbawa `Asia/Seoul`)

Nasa [checklist sa deployment](deployment-checklist.md#mga-environment-variable) ang buong listahan ng mga environment variable sa production.

## 4. Pag-install

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

Pinatatakbo ng `setup_install`, ayon sa pagkakasunod-sunod: ang mga migration (sa koneksiyon ng `app_migrator`), mahahalagang datos (mga template ng tungkulin at pag-sync ng pahintulot, mga bansa, mga wika, mga uri ng lookup, mga uri ng yunit ng organisasyon, mga uri ng pagbabago ng katayuan, mga bundle ng panuntunan sa pagpapatala), ang mga default ng institusyon (default na wika, time zone, pangalan ng institusyon), ang pagtatakda ng iskala ng marka, mga profile sa pag-install at ang unang administrator. Sa mga deployment script, patakbuhin ito gamit ang `--force` at mga option; binabasa ang password ng administrator mula sa standard input.

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

Mga profile sa pag-install (`--profile=`, maaaring ibigay nang higit sa isang beses)

| Key | Nilalaman |
|---|---|
| `korean-university` | Mga uri ng termino na spring/summer/fall/winter, ang iskala ng marka na 4.5, mga kategorya ng asignatura, mga period mula 09:00, mga uri ng silid, mga uri ng admisyon at dokumento ng aplikasyon, ang default na form ng ebalwasyon ng asignatura, mga uri ng sertipiko na may mga template sa apat na wika |
| `yust-legacy` | Lahat ng nasa `korean-university`, dagdag ang mga limitasyon ng units ayon sa taon ng admisyon at para sa nursing, mga asignatura sa credit bank na labas sa limitasyon, ang iskala ng marka na 4.3 at ang patakaran nito sa pagmamarka |

Kapag walang profile, ilagay ang mga ito sa panel ng administrasyon. Kapag inilapat muli ang isang profile sa ibang pagkakataon, pinapanatili ang mga value na binago ng mga administrator. Hindi na mababago ang iskala ng marka kapag naitakda na (iniimbak sa iskalang iyon ang mga marka at GPA).

Naka-disable ang `createsuperuser` ng Django. Ginagawa lamang ang unang administrator gamit ang `setup_install` o `security_create_administrator` ([sanggunian ng mga command](commands.md)).

Matapos ang pag-install, inilalagay ng mga administrator ng negosyo ang sangguniang datos ayon sa [kabanata 5 ng manwal ng administrator, pagkakasunod-sunod ng unang pag-set up](../admin/05-institution-setup.md). Irehistro ang mga proseso ng server (gunicorn, Celery worker, beat) gaya ng inilalarawan sa [checklist sa deployment](deployment-checklist.md) at [mga naka-iskedyul na job](scheduled-jobs.md).

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
| Mailpit (mailbox para sa development) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite dev server (opsiyonal, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

Ang production image ay ang target na `production` ng `Dockerfile` (ang default). Pinatatakbo nito ang `compilemessages` at `collectstatic` sa oras ng build at sinisimulan ang gunicorn. Pinatatakbo rin ng parehong image ang worker at beat (`uv run --no-sync celery -A config worker|beat`).

## 5. Pag-verify ng pag-install

1. Mag-sign in bilang unang administrator sa `/accounts/login/`. Nagbubukas ang `/admin/` at ipinapakita ng sidebar ang **Mga user at access**, **Audit** at **Mga setting**.
2. Sa panel ng administrasyon, itakda ang patakaran sa two-factor sa ilalim ng **Mga setting > Seguridad**.
3. I-enroll ang two-factor authentication para sa administrator (**Seguridad** sa portal, `/portal/security/`).
4. Suriin ang PDF service gamit ang `uv run manage.py pdf_sample`.
5. Sa panel ng administrasyon, tiyaking ipinapakita ng **Audit > Mga pagbabago ng datos** ang pag-install bilang `system:command:setup_install`.
6. Tiyaking walang iniuulat na babala sa production ang `uv run manage.py check --deploy` at sumasagot ang `GET /api/v1/health/` ng `{"status": "ok"}` (dapat nakatakbo na ang beat nang isang minuto).

## 6. Mga update

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

Iangkop ang mga pangalan ng service sa iyong installation. Sundin ang [checklist sa deployment](deployment-checklist.md#pamamaraan-ng-deployment) para sa backup at mga pagsusuri sa paligid ng isang update.
