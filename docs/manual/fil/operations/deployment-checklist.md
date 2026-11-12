# Checklist sa deployment at mga setting ng gunicorn at Python

- Para kanino: mga IT operator
- Kaugnay: [pag-install](installation.md), [pamamahala ng key](security-keys.md), [mga naka-iskedyul na job](scheduled-jobs.md), [load testing](load-testing.md)

## Python at mga dependency

- Gamitin ang pinakabagong patch release ng **Python 3.14**. Kapag gumagawa ng container o server image, huwag i-pin ang patch version ng Python; kunin ang pinakabago (`python:3.14-slim` sa `Dockerfile`).
- Naka-lock sa `uv.lock` ang mga dependency ng Python. Laging gumagamit ang mga installation sa production ng `uv sync --frozen --no-dev` (nabibigo ito kung hindi tugma ang lock file). Hindi kailanman umaabot sa production ang mga development tool (pytest, ruff, mypy, Playwright).
- Kapag naglabas ang Django ng security release, mag-upgrade gamit ang `uv lock --upgrade-package django`, patakbuhin ang mga test at i-deploy. Suriin ang mga kahinaan ng dependency gaya ng ginagawa ng CI: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`.
- Nagbababala ang `uv run manage.py check --deploy` tungkol sa mga setting ng production (`DEBUG`, HTTPS, mga cookie, HSTS, haba ng secret key). Dapat walang babala ang bawat deployment.

## gunicorn at Nginx

| Item | Value | Dahilan |
|---|---|---|
| Pagpapatakbo ng gunicorn | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, mga sync worker. Nagmumula sa mga environment variable ang bilang ng worker at ang laki ng connection pool; nasa [load testing](load-testing.md) ang pangangatwiran |
| Bind ng gunicorn | `127.0.0.1:8000` o isang Unix socket | Huwag kailanman direktang ilantad ang gunicorn; laging ilagay ito sa likod ng Nginx |
| Pag-restart ng worker | `HUP` sa deploy (systemd `reload`) | Tinatapos ang mga kasalukuyang request at pinapalitan ang mga worker ng bagong code |
| Mga koneksiyon sa DB | Kapag `DB_POOL=true`, isang psycopg connection pool bawat worker (`DB_POOL_MIN`, `DB_POOL_MAX`) | Dapat manatiling mas mababa sa `max_connections` ng PostgreSQL ang mga worker × `DB_POOL_MAX` + mga koneksiyon ng Celery. Inaalis ang actor ng DB session ng koneksiyong ibinalik sa pool (`ninefruits.core.pool.reset_connection`) |
| Nginx `client_max_body_size` | `32m` | Pinakamataas na limitasyon para sa mga dokumento ng admisyon, patunay ng pagsusulit at pag-upload ng larawan (may palugit sa itaas ng 5MB at 2MB na validation ng application) |
| Mga static file sa Nginx | `location /static/ { alias <repository>/staticfiles/; }` | Ang Nginx mismo ang naghahatid ng output ng `collectstatic` |
| Mga pribadong file | **Huwag kailanman i-map** ang `PRIVATE_MEDIA_ROOT` (default `storage/private`) sa Nginx | Dina-download lamang ang mga larawan, dokumento ng aplikasyon at PDF ng sertipiko sa pamamagitan ng mga view na sumusuri ng pahintulot |
| Mga header ng Nginx | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, opsiyonal na `X-Request-Id $request_id` | Address ng client, pagtukoy sa HTTPS, pagsubaybay bawat request |
| Gotenberg, Redis, PostgreSQL | Mga panloob na address lamang | Hindi kailanman inilalantad sa labas |

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

### Mga proxy at ang address ng client

Ginagamit ng mga limitasyon sa pag-sign in, mga rate limit ng API at mga IP address sa mga rekord ng audit ang address ng client na tinutukoy ng `ninefruits.core.http.client_ip`.

- `TRUSTED_PROXY_COUNT`: ang bilang ng mga reverse proxy sa harap ng application na nagdadagdag sa `X-Forwarded-For`. `1` para sa iisang Nginx, `2` para sa load balancer at Nginx. Ginagamit ng `0` (ang default) ang `REMOTE_ADDR`. Ang entry na ganito karaming puwesto mula sa kanan ang address ng client; hindi kailanman pinagkakatiwalaan ang mga entry na mas nasa kaliwa (ipinadala ng client).
- **Kung mas mababa ang value kaysa sa tunay na bilang ng proxy**, lumilitaw na nagmumula sa address ng Nginx ang bawat user at sabay na ipinatutupad sa buong campus ang limitasyon sa pag-sign in. **Kung mas mataas**, pinagkakatiwalaan ng application ang `X-Forwarded-For` na ipinadala ng client, at malulusutan ang mga limitasyon. Matapos mag-deploy, tiyaking tunay na address ng mga user ang mga IP address sa ilalim ng **Audit > Mga pangyayaring pangseguridad** sa panel ng administrasyon.
- `LOGIN_RATE_LIMIT_PER_IP`: mga pagtatangkang mag-sign in bawat address ng client (django-allauth, default `30/m/ip`). Walang ganitong limitasyon ang orihinal. Kung lumalabas ang buong campus sa iisang NAT address, masyadong mababa ito para sa unang umaga ng pagpapatala; taasan ito (halimbawa `300/m/ip`). Ang walang laman ay nangangahulugang walang limitasyon bawat address (gaya ng sa orihinal). Ipinatutupad ang limitasyon ng pagkabigo bawat account (5 bawat minuto) at ang pag-lock ng account anuman ang value na ito.

## Mga environment variable

Hawak ng `.env.example` ang mga default para sa development. Sa production, ipasok ang mga lihim mula sa secret store.

| Variable | Value sa production | Mga tala |
|---|---|---|
| `DJANGO_ENV` | `production` | Tinatanggihan ang `setup_demo` at inaalis ang badge ng environment sa panel ng administrasyon |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, mga secure cookie |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | Secret store | [Pamamahala ng key](security-keys.md). Kapag nagro-rotate, napupunta ang mga dating key sa `DJANGO_SECRET_KEY_FALLBACKS` |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | Mga listahang pinaghihiwalay ng kuwit |
| `APP_URL` | `https://sis.example.ac.kr` | Mga link sa mail, mga QR code ng beripikasyon ng sertipiko |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | Secret store | Kapag nawala, hindi na made-decrypt ang personal na datos |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | Application at Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | Ginagamit ng `migrate`, `setup_install`, `audit_seal` at `audit_prune`. Itago ang password sa server lamang na nagpapatakbo ng mga deployment at sa nagpapatakbo ng pag-seal ng audit (`audit_seal`) |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, ang value mula sa [load testing](load-testing.md), `60`, `2000`, `127.0.0.1` | Binabasa ng `config/gunicorn.py`. 2 bawat CPU core + 1 ang default na bilang ng worker. Sinasabi lamang ng `GUNICORN_FORWARDED_ALLOW_IPS` kung kaninong `X-Forwarded-Proto` ang pinagkakatiwalaan ng gunicorn; nagmumula sa `TRUSTED_PROXY_COUNT` ang address ng client |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | Mga value na napagpasyahan sa [load testing](load-testing.md): `true`, `1`, `2`, `2` | Ino-on ng `DB_PREPARE_THRESHOLD` ang mga prepared statement (binabawasan ang gastos sa pagpaplano ng RLS query); ino-off ito ng 0 |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Panloob na Redis | `REDIS_URL` ang default ng broker at mga resulta |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | Ang SMTP relay ng unibersidad | Mga imbitasyon, mga code ng two-factor, mga abiso sa pagpapatala at marka |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | Panloob na address, `60` | |
| `PRIVATE_MEDIA_ROOT` | Disk na bina-back up | Pribadong imbakan ng file |
| `TRUSTED_PROXY_COUNT` | Karaniwang `1` | Seksiyon sa itaas |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` o mas mataas | Seksiyon sa itaas |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | Kapag unang ini-enable ang HTTPS, subukan muna ang maikling HSTS (`300`) bago ito taasan |
| `SESSION_LIFETIME_MINUTES` | `120` | Tagal ng session na naka-sign in |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, ang time zone ng institusyon | Mga oras ng server at naka-iskedyul na job sa UTC, mga screen sa time zone ng institusyon |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | Mga default | [Gabay sa integrasyon ng LMS](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | Napupunta ang mga log sa standard output bilang isang JSON object bawat linya |
| `VITE_DEV_MODE` | `false` | Ginagamit ng production ang build output (`static/dist/manifest.json`) |

## Pamamaraan ng deployment

1. Mag-backup ([backup at restore](backup-restore.md)) at patakbuhin ang `uv run manage.py audit_verify_chain`.
2. I-deploy ang code: `git pull` (o bagong image), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force`: mga migration (awtomatikong lumilipat sa koneksiyon ng `app_migrator`), ni-refresh na mahahalagang datos (pinapanatili ang mga pagbabago ng administrator), pag-sync ng katalogo ng pahintulot. Kapag hiwalay na pinatatakbo ang mga migration, awtomatiko ring ginagamit ng `uv run manage.py migrate` ang `app_migrator`. Walang paraan para patakbuhin ang DDL bilang `app_runtime`.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. Pinatatakbo ng production Docker image ang dalawa sa oras ng build.
5. I-restart ang mga proseso: `reload` ng gunicorn (HUP), ang Celery worker (pinatatapos ng TERM ang mga tumatakbong task; dahil sa `acks_late`, muling tumatakbo ang naantalang task), Celery beat. Magpatakbo ng **eksaktong isang proseso ng beat** sa lahat ng server. Kapag dalawa, dalawang beses na naka-queue ang bawat naka-iskedyul na job (pinipigilan ng Redis lock ng bawat job ang sabay na pagtakbo, hindi ang dobleng pag-queue).
6. I-verify: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (exit code 0), `GET /api/v1/health/` (`ok`), pag-sign in sa panel ng administrasyon, `uv run manage.py pdf_sample`. Tiyakin sa Flower na nakakonekta ang worker.

## Mga regular na pagsusuri

| Dalas | Gawain |
|---|---|
| Araw-araw (awtomatiko) | `audit.seal`, `lms.reconcile`, pagpapalaya ng mga nakareserbang upuan sa pagpapatala, pag-akyat mula sa waitlist, pag-expire ng mga draft ng aplikasyon ([mga naka-iskedyul na job](scheduled-jobs.md)) |
| Lingguhan | `/api/v1/health/` at `check --deploy`, mga security update ng Python, OS at dependency (`pip-audit`), mga nabigong task sa Flower |
| Buwanan | `media_prune_orphans --dry-run`, pagsasanay sa restore ng backup, `audit_verify_chain` |
| Bawat termino | Suriin ang mga pagtatalaga ng tungkulin (mga taong umalis o lumipat), i-prune ang mga rekord ng audit na lampas na sa panahon ng pagpapanatili (`audit_prune`), bago ang pagpapatala suriin muli ang `LOGIN_RATE_LIMIT_PER_IP` at ang bilang ng worker |
