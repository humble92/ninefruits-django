# ລາຍການກວດສອບການນຳໃຊ້ລະບົບ ແລະ ການຕັ້ງຄ່າ gunicorn ແລະ Python

- ກຸ່ມເປົ້າໝາຍ: ຜູ້ປະຕິບັດງານ IT
- ກ່ຽວຂ້ອງ: [ການຕິດຕັ້ງ](installation.md), [ການຄຸ້ມຄອງກະແຈ](security-keys.md), [ວຽກຕາມກຳນົດເວລາ](scheduled-jobs.md), [ການທົດສອບພາລະ](load-testing.md)

## Python ແລະ dependency

- ໃຊ້ການປ່ອຍ patch ລ່າສຸດຂອງ **Python 3.14**. ເມື່ອສ້າງ image ຂອງ container ຫຼື ເຊີບເວີ ຢ່າຕຶງເວີຊັນ patch ຂອງ Python ໄວ້ ແຕ່ໃຫ້ຮັບເວີຊັນລ່າສຸດ (`python:3.14-slim` ໃນ `Dockerfile`).
- dependency ຂອງ Python ຖືກລັອກໄວ້ໃນ `uv.lock`. ການຕິດຕັ້ງສຳລັບການນຳໃຊ້ຈິງໃຊ້ `uv sync --frozen --no-dev` ສະເໝີ (ຈະລົ້ມເຫຼວຖ້າບໍ່ກົງກັບໄຟລ໌ລັອກ). ເຄື່ອງມືພັດທະນາ (pytest, ruff, mypy, Playwright) ບໍ່ເຂົ້າໄປໃນສະພາບແວດລ້ອມນຳໃຊ້ຈິງ.
- ເມື່ອ Django ປ່ອຍເວີຊັນຄວາມປອດໄພ ໃຫ້ອັບເກຣດດ້ວຍ `uv lock --upgrade-package django` ແລ້ວທົດສອບກ່ອນນຳໃຊ້. ກວດຊ່ອງໂຫວ່ຂອງ dependency ຄືກັບ CI: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`.
- `uv run manage.py check --deploy` ສະແດງຄຳເຕືອນການຕັ້ງຄ່າສຳລັບການນຳໃຊ້ຈິງ (`DEBUG`, HTTPS, cookie, HSTS, ຄວາມຍາວຂອງກະແຈລັບ). ທຸກຄັ້ງທີ່ນຳໃຊ້ລະບົບຕ້ອງມີຄຳເຕືອນ 0 ລາຍການ.

## gunicorn ແລະ Nginx

| ລາຍການ | ຄ່າ | ເຫດຜົນ |
|---|---|---|
| ການແລ່ນ gunicorn | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, sync worker. ຈຳນວນ worker ແລະ ຂະໜາດ connection pool ກຳນົດດ້ວຍຕົວແປສະພາບແວດລ້ອມ ແລະ ເຫດຜົນຢູ່ໃນ [ການທົດສອບພາລະ](load-testing.md) |
| bind ຂອງ gunicorn | `127.0.0.1:8000` ຫຼື Unix socket | ບໍ່ເປີດ gunicorn ສູ່ພາຍນອກໂດຍກົງ. ວາງໄວ້ຫຼັງ Nginx ສະເໝີ |
| ການເລີ່ມ worker ໃໝ່ | `HUP` ເມື່ອນຳໃຊ້ (systemd `reload`) | ເຮັດຄຳຮ້ອງຂໍທີ່ກຳລັງດຳເນີນຢູ່ໃຫ້ແລ້ວ ແລະ ປ່ຽນ worker ເປັນໂຄດໃໝ່ |
| ການເຊື່ອມຕໍ່ DB | ເມື່ອ `DB_POOL=true` ມີ connection pool ຂອງ psycopg ຕໍ່ worker (`DB_POOL_MIN`, `DB_POOL_MAX`) | ຈຳນວນ worker × `DB_POOL_MAX` + ການເຊື່ອມຕໍ່ຂອງ Celery ຕ້ອງນ້ອຍກວ່າ `max_connections` ຂອງ PostgreSQL. ການເຊື່ອມຕໍ່ທີ່ກັບຄືນ pool ຈະຖືກລ້າງຜູ້ປະຕິບັດຂອງເຊສຊັນ DB (`ninefruits.core.pool.reset_connection`) |
| `client_max_body_size` ຂອງ Nginx | `32m` | ເພດານການອັບໂຫຼດເອກະສານສະໝັກເຂົ້າຮຽນ, ຫຼັກຖານການສອບເສັງ ແລະ ຮູບຖ່າຍ (ມີຊ່ອງຫວ່າງຫຼາຍກວ່າການກວດຂອງແອັບທີ່ 5MB ແລະ 2MB) |
| ໄຟລ໌ static ຂອງ Nginx | `location /static/ { alias <repository>/staticfiles/; }` | Nginx ໃຫ້ບໍລິການຜົນຂອງ `collectstatic` ເອງ |
| ໄຟລ໌ສ່ວນຕົວ | **ຢ່າເຊື່ອມ** `PRIVATE_MEDIA_ROOT` (ຄ່າເລີ່ມຕົ້ນ `storage/private`) ເຂົ້າກັບ Nginx | ຮູບຖ່າຍ, ເອກະສານສະໝັກ ແລະ PDF ໃບຢັ້ງຢືນ ດາວໂຫຼດໄດ້ສະເພາະຜ່ານໜ້າຈໍທີ່ກວດສິດເທົ່ານັ້ນ |
| header ຂອງ Nginx | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, ທາງເລືອກ: `X-Request-Id $request_id` | ທີ່ຢູ່ຂອງລູກຂ່າຍ, ການຕັດສິນ HTTPS, ການຕິດຕາມລະດັບຄຳຮ້ອງຂໍ |
| Gotenberg, Redis, PostgreSQL | ທີ່ຢູ່ເຄືອຂ່າຍພາຍໃນເທົ່ານັ້ນ | ບໍ່ເປີດເຜີຍສູ່ພາຍນອກ |

```nginx
server {
    listen 443 ssl;
    server_name sis.example.edu.la;
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

### proxy ແລະ ທີ່ຢູ່ຂອງລູກຂ່າຍ

ຂີດຈຳກັດການເຂົ້າສູ່ລະບົບ, ຂີດຈຳກັດຄຳຮ້ອງຂໍ API ແລະ ທີ່ຢູ່ IP ໃນບັນທຶກການກວດສອບ ໃຊ້ທີ່ຢູ່ຂອງລູກຂ່າຍທີ່ `ninefruits.core.http.client_ip` ກຳນົດ.

- `TRUSTED_PROXY_COUNT`: ຈຳນວນ reverse proxy ທີ່ຢູ່ຂ້າງໜ້າແອັບພລິເຄຊັນ ເຊິ່ງຕໍ່ທ້າຍທີ່ຢູ່ເຂົ້າໃນ `X-Forwarded-For`. Nginx ໂຕດຽວແມ່ນ `1`, load balancer + Nginx ແມ່ນ `2`. `0` (ຄ່າເລີ່ມຕົ້ນ) ຈະໃຊ້ `REMOTE_ADDR`. ລາຍການທີ່ນັບຈາກຂວາມືຕາມຈຳນວນນີ້ຄືທີ່ຢູ່ຂອງລູກຂ່າຍ ແລະ ລາຍການທີ່ຢູ່ຊ້າຍກວ່ານັ້ນ (ຄ່າທີ່ລູກຂ່າຍສົ່ງມາ) ຈະບໍ່ຖືກເຊື່ອ.
- **ຖ້າຄ່ານ້ອຍກວ່າຈຳນວນ proxy ຕົວຈິງ** ຜູ້ໃຊ້ທຸກຄົນຈະເບິ່ງຄືມາຈາກທີ່ຢູ່ Nginx ດຽວ ແລະ ຂີດຈຳກັດການເຂົ້າສູ່ລະບົບຈະນຳໃຊ້ກັບທັງມະຫາວິທະຍາໄລພ້ອມກັນ. **ຖ້າຫຼາຍກວ່າ** ແອັບຈະເຊື່ອ `X-Forwarded-For` ທີ່ລູກຂ່າຍສົ່ງມາ ແລະ ສາມາດຫຼົບຫຼີກຂີດຈຳກັດໄດ້. ຫຼັງນຳໃຊ້ລະບົບ ໃຫ້ກວດວ່າທີ່ຢູ່ IP ໃນ **ການກວດສອບ > ເຫດການຄວາມປອດໄພ** ຂອງໜ້າບໍລິຫານແມ່ນທີ່ຢູ່ຂອງຜູ້ໃຊ້ຕົວຈິງ.
- `LOGIN_RATE_LIMIT_PER_IP`: ຈຳນວນການພະຍາຍາມເຂົ້າສູ່ລະບົບຕໍ່ທີ່ຢູ່ລູກຂ່າຍ (django-allauth, ຄ່າເລີ່ມຕົ້ນ `30/m/ip`). ຕົ້ນສະບັບບໍ່ມີຂີດຈຳກັດນີ້. ຖ້າທັງວິທະຍາເຂດອອກອິນເຕີເນັດຜ່ານທີ່ຢູ່ NAT ດຽວ ຄ່ານີ້ຈະບໍ່ພໍໃນເຊົ້າມື້ທຳອິດຂອງການລົງທະບຽນຮຽນ ໃຫ້ເພີ່ມຂຶ້ນ (ຕົວຢ່າງ `300/m/ip`). ຖ້າປະວ່າງ ຈະບໍ່ມີຂີດຈຳກັດຕໍ່ທີ່ຢູ່ (ຄືກັບຕົ້ນສະບັບ). ຂີດຈຳກັດການລົ້ມເຫຼວຕໍ່ບັນຊີ (5 ຄັ້ງຕໍ່ນາທີ) ແລະ ການລັອກບັນຊີ ເຮັດວຽກໂດຍບໍ່ຂຶ້ນກັບຄ່ານີ້.

## ຕົວແປສະພາບແວດລ້ອມ

`.env.example` ແມ່ນຄ່າເລີ່ມຕົ້ນສຳລັບການພັດທະນາ. ໃນການນຳໃຊ້ຈິງ ໃຫ້ສີດຄ່າລັບຈາກບ່ອນເກັບຄວາມລັບ.

| ຕົວແປ | ຄ່າສຳລັບການນຳໃຊ້ຈິງ | ໝາຍເຫດ |
|---|---|---|
| `DJANGO_ENV` | `production` | ປະຕິເສດ `setup_demo` ແລະ ເອົາປ້າຍສະພາບແວດລ້ອມອອກຈາກໜ້າບໍລິຫານ |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, cookie ທີ່ປອດໄພ |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | ບ່ອນເກັບຄວາມລັບ | [ການຄຸ້ມຄອງກະແຈ](security-keys.md). ເມື່ອປ່ຽນ ກະແຈເກົ່າໃສ່ໃນ `DJANGO_SECRET_KEY_FALLBACKS` |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.edu.la`, `https://sis.example.edu.la` | ລາຍການຂັ້ນດ້ວຍເຄື່ອງໝາຍ `,` |
| `APP_URL` | `https://sis.example.edu.la` | ລິ້ງໃນເມວ, QR ກວດຄວາມແທ້ຂອງໃບຢັ້ງຢືນ |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | ບ່ອນເກັບຄວາມລັບ | ຖ້າເສຍ ຈະຖອດລະຫັດຂໍ້ມູນສ່ວນບຸກຄົນບໍ່ໄດ້ |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | ແອັບພລິເຄຊັນ, Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | ໃຊ້ໂດຍ `migrate`, `setup_install`, `audit_seal`, `audit_prune`. ເກັບລະຫັດຜ່ານໄວ້ສະເພາະເຊີບເວີທີ່ແລ່ນການນຳໃຊ້ລະບົບ ແລະ ເຊີບເວີທີ່ແລ່ນການປະທັບຕາບັນທຶກການກວດສອບ (`audit_seal`) |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, ຄ່າຈາກ [ການທົດສອບພາລະ](load-testing.md), `60`, `2000`, `127.0.0.1` | `config/gunicorn.py` ອ່ານຄ່າເຫຼົ່ານີ້. ຈຳນວນ worker ເລີ່ມຕົ້ນແມ່ນ 2 ຕໍ່ CPU core + 1. `GUNICORN_FORWARDED_ALLOW_IPS` ກຳນົດພຽງວ່າ gunicorn ເຊື່ອ `X-Forwarded-Proto` ຈາກໃຜ; ທີ່ຢູ່ຂອງລູກຂ່າຍມາຈາກ `TRUSTED_PROXY_COUNT` |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | ຄ່າທີ່ຕັດສິນໃນ [ການທົດສອບພາລະ](load-testing.md): `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` ເປີດ prepared statement (ຫຼຸດຕົ້ນທຶນການວາງແຜນຄິວຣີຂອງ RLS); 0 ປິດ |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis ໃນເຄືອຂ່າຍພາຍໃນ | broker ແລະ ຜົນໃຊ້ `REDIS_URL` ເປັນຄ່າເລີ່ມຕົ້ນ |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | SMTP relay ຂອງມະຫາວິທະຍາໄລ | ການເຊີນ, ລະຫັດການຢືນຢັນສອງຂັ້ນຕອນ, ການແຈ້ງເຕືອນການລົງທະບຽນຮຽນ ແລະ ເກຣດ |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | ທີ່ຢູ່ພາຍໃນ, `60` | |
| `PRIVATE_MEDIA_ROOT` | ດິສທີ່ຖືກສຳຮອງ | ບ່ອນເກັບໄຟລ໌ສ່ວນຕົວ |
| `TRUSTED_PROXY_COUNT` | ປົກກະຕິ `1` | ພາກຂ້າງເທິງ |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` ຫຼື ຫຼາຍກວ່າ | ພາກຂ້າງເທິງ |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | ເມື່ອເປີດ HTTPS ຄັ້ງທຳອິດ ໃຫ້ທົດລອງ HSTS ສັ້ນໆ (`300`) ກ່ອນແລ້ວຈຶ່ງເພີ່ມ |
| `SESSION_LIFETIME_MINUTES` | `120` | ອາຍຸຂອງເຊສຊັນການເຂົ້າສູ່ລະບົບ |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, ເຂດເວລາຂອງສະຖາບັນ | ເວລາເຊີບເວີ ແລະ ວຽກຕາມກຳນົດເວລາໃຊ້ UTC, ການສະແດງໃນໜ້າຈໍໃຊ້ເຂດເວລາຂອງສະຖາບັນ |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | ຄ່າເລີ່ມຕົ້ນ | [ຄູ່ມືການເຊື່ອມຕໍ່ LMS](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | log ອອກທາງ standard output ເປັນ JSON ແຖວລະອັນ |
| `VITE_DEV_MODE` | `false` | ການນຳໃຊ້ຈິງໃຊ້ຜົນການ build (`static/dist/manifest.json`) |

## ຂັ້ນຕອນການນຳໃຊ້ລະບົບ

1. ສຳຮອງຂໍ້ມູນ ([ການສຳຮອງ ແລະ ກູ້ຄືນຂໍ້ມູນ](backup-restore.md)) ແລະ ແລ່ນ `uv run manage.py audit_verify_chain`.
2. ນຳໃຊ້ໂຄດ: `git pull` (ຫຼື image ໃໝ່), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force`: migration (ປ່ຽນໄປໃຊ້ການເຊື່ອມຕໍ່ `app_migrator` ອັດຕະໂນມັດ), ອັບເດດຂໍ້ມູນທີ່ຈຳເປັນ (ຮັກສາການແກ້ໄຂຂອງຜູ້ບໍລິຫານ), ຊິງຄ໌ລາຍການສິດ. ເມື່ອແລ່ນ migration ຢ່າງດຽວ `uv run manage.py migrate` ກໍໃຊ້ `app_migrator` ອັດຕະໂນມັດຄືກັນ. ບໍ່ມີວິທີແລ່ນ DDL ດ້ວຍ `app_runtime`.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. image Docker ສຳລັບການນຳໃຊ້ຈິງແລ່ນທັງສອງຄຳສັ່ງໃນເວລາ build.
5. ເລີ່ມໂປຣເຊສໃໝ່: gunicorn `reload` (HUP), ເລີ່ມ Celery worker ໃໝ່ (TERM ຈະລໍໃຫ້ວຽກທີ່ກຳລັງແລ່ນສຳເລັດກ່ອນ; ເພາະເປັນ `acks_late` ວຽກທີ່ຖືກຂັດຈັງຫວະຈະຖືກແລ່ນຄືນ), ເລີ່ມ Celery beat ໃໝ່. **ແລ່ນ beat ພຽງໂປຣເຊສດຽວໃນທຸກເຊີບເວີ.** ຖ້າມີສອງ ວຽກຕາມກຳນົດເວລາທຸກວຽກຈະຖືກໃສ່ຄິວສອງເທື່ອ (Redis lock ຂອງແຕ່ລະວຽກປ້ອງກັນການແລ່ນພ້ອມກັນ ແຕ່ບໍ່ປ້ອງກັນການໃສ່ຄິວຊ້ຳ).
6. ກວດ: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (ລະຫັດອອກ 0), `GET /api/v1/health/` (`ok`), ການເຂົ້າສູ່ໜ້າບໍລິຫານ, `uv run manage.py pdf_sample`. ກວດໃນ Flower ວ່າ worker ເຊື່ອມຕໍ່ແລ້ວ.

## ການກວດກາຕາມກຳນົດ

| ຄວາມຖີ່ | ສິ່ງທີ່ຕ້ອງເຮັດ |
|---|---|
| ທຸກວັນ (ອັດຕະໂນມັດ) | `audit.seal`, `lms.reconcile`, ປ່ອຍບ່ອນນັ່ງທີ່ຈອງໄວ້, ເລື່ອນຂຶ້ນຈາກລາຍຊື່ລໍຖ້າ, ໝົດອາຍຸໃບສະໝັກທີ່ຍັງຮ່າງຢູ່ ([ວຽກຕາມກຳນົດເວລາ](scheduled-jobs.md)) |
| ທຸກອາທິດ | `/api/v1/health/` ແລະ `check --deploy`, ກວດການອັບເດດຄວາມປອດໄພຂອງ Python, OS ແລະ dependency (`pip-audit`), ກວດວຽກທີ່ລົ້ມເຫຼວໃນ Flower |
| ທຸກເດືອນ | `media_prune_orphans --dry-run`, ຝຶກຊ້ອມກູ້ຄືນຈາກການສຳຮອງຂໍ້ມູນ, `audit_verify_chain` |
| ທຸກພາກຮຽນ | ກວດການມອບບົດບາດ (ຜູ້ທີ່ລາອອກ ຫຼື ຍ້າຍ), ລ້າງບັນທຶກການກວດສອບທີ່ເກີນໄລຍະເກັບຮັກສາ (`audit_prune`), ກ່ອນການລົງທະບຽນຮຽນ ໃຫ້ກວດ `LOGIN_RATE_LIMIT_PER_IP` ແລະ ຈຳນວນ worker ຄືນ |
