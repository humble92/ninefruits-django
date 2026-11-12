# Байршуулалтын хяналтын хуудас ба gunicorn, Python-ийн тохиргоо

- Зориулалт: МТ-ийн ашиглалтын ажилтнууд
- Холбогдох: [суулгалт](installation.md), [түлхүүрийн удирдлага](security-keys.md), [төлөвлөгдсөн ажлууд](scheduled-jobs.md), [ачааллын тест](load-testing.md)

## Python ба хамаарлууд

- **Python 3.14**-ийн хамгийн сүүлийн patch хувилбарыг ашиглана. Контейнер эсвэл серверийн image бүтээхдээ Python-ийн patch хувилбарыг тогтоохгүй; хамгийн сүүлийнхийг авна (`Dockerfile` дахь `python:3.14-slim`).
- Python-ийн хамаарлуудыг `uv.lock`-д түгжинэ. Production-ий суулгалт үргэлж `uv sync --frozen --no-dev` ашиглана (lock файл зөрвөл амжилтгүй болно). Хөгжүүлэлтийн хэрэгслүүд (pytest, ruff, mypy, Playwright) production-д хэзээ ч хүрэхгүй.
- Django аюулгүй байдлын хувилбар гаргахад `uv lock --upgrade-package django`-оор шинэчилж, тестүүдийг ажиллуулаад байршуулна. Хамаарлын эмзэг байдлыг CI-тай адил шалгана: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`.
- `uv run manage.py check --deploy` production-ийн тохиргооны (`DEBUG`, HTTPS, cookie, HSTS, нууц түлхүүрийн урт) тухай анхааруулна. Байршуулалт бүр тэг анхааруулгатай байх ёстой.

## gunicorn ба Nginx

| Зүйл | Утга | Шалтгаан |
|---|---|---|
| gunicorn ажиллуулах | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, sync worker. Worker-ийн тоо болон холболтын санг орчны хувьсагчаас авна; үндэслэл нь [ачааллын тест](load-testing.md)-д |
| gunicorn bind | `127.0.0.1:8000` эсвэл Unix socket | gunicorn-ийг хэзээ ч шууд ил гаргахгүй; үргэлж Nginx-ийн ард байрлуулна |
| Worker дахин эхлүүлэх | Байршуулахад `HUP` (systemd `reload`) | Явагдаж буй хүсэлтүүдийг дуусгаад worker-уудыг шинэ кодоор солино |
| DB холболт | `DB_POOL=true` бол worker тус бүрт psycopg холболтын сан (`DB_POOL_MIN`, `DB_POOL_MAX`) | Worker × `DB_POOL_MAX` + Celery-ийн холболт нь PostgreSQL-ийн `max_connections`-аас бага байх ёстой. Сан руу буцаасан холболтын DB сессийн гүйцэтгэгчийг цэвэрлэнэ (`ninefruits.core.pool.reset_connection`) |
| Nginx `client_max_body_size` | `32m` | Элсэлтийн баримт, шалгалтын нотлох баримт, зураг байршуулах дээд хязгаар (аппликейшны 5MB, 2MB шалгалтаас илүү зай) |
| Nginx статик файл | `location /static/ { alias <repository>/staticfiles/; }` | Nginx `collectstatic`-ийн гаралтыг өөрөө түгээнэ |
| Хувийн файл | `PRIVATE_MEDIA_ROOT`-ийг (анхдагч `storage/private`) Nginx-д **хэзээ ч холбохгүй** | Зураг, өргөдлийн баримт, тодорхойлолтын PDF-ийг зөвхөн эрх шалгадаг view-ээр татна |
| Nginx-ийн толгой | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, сонголтоор `X-Request-Id $request_id` | Клиентийн хаяг, HTTPS илрүүлэх, хүсэлт тус бүрийг мөрдөх |
| Gotenberg, Redis, PostgreSQL | Зөвхөн дотоод хаяг | Гадагш хэзээ ч ил гаргахгүй |

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

### Прокси ба клиентийн хаяг

Нэвтрэлтийн хязгаар, API-ийн хурдны хязгаар болон аудитын бичлэг дэх IP хаяг нь `ninefruits.core.http.client_ip`-ийн тодорхойлсон клиентийн хаягийг ашиглана.

- `TRUSTED_PROXY_COUNT`: аппликейшны өмнө байх, `X-Forwarded-For`-д нэмдэг reverse proxy-ийн тоо. Ганц Nginx бол `1`, ачаалал тэнцвэржүүлэгч дээр нь Nginx бол `2`. `0` (анхдагч) бол `REMOTE_ADDR`-ийг ашиглана. Баруун талаас ийм тооны байранд байгаа бичлэг нь клиентийн хаяг; түүнээс зүүн талын (клиентийн илгээсэн) бичлэгт хэзээ ч итгэхгүй.
- **Утга бодит проксины тооноос бага бол** бүх хэрэглэгч Nginx-ийн хаягаас ирсэн мэт харагдаж, нэвтрэлтийн хязгаар бүх кампусад нэг дор үйлчилнэ. **Их бол** аппликейшн клиентийн илгээсэн `X-Forwarded-For`-д итгэж, хязгаарыг тойрох боломжтой болно. Байршуулсны дараа удирдлагын самбарын **Аудит > Аюулгүй байдлын үйл явдлууд** дахь IP хаягууд бодит хэрэглэгчийн хаяг эсэхийг шалгана.
- `LOGIN_RATE_LIMIT_PER_IP`: клиентийн хаяг тус бүрийн нэвтрэх оролдлого (django-allauth, анхдагч `30/m/ip`). Анхны системд ийм хязгаар байгаагүй. Бүх кампус нэг NAT хаягаар гардаг бол хичээл сонголтын эхний өглөөнд энэ хэт бага; нэмэгдүүлнэ (жишээ нь `300/m/ip`). Хоосон бол хаяг тус бүрийн хязгааргүй (анхны системтэй адил). Бүртгэл тус бүрийн амжилтгүй оролдлогын хязгаар (минутад 5) болон бүртгэлийн түгжээ энэ утгаас үл хамааран үйлчилнэ.

## Орчны хувьсагчид

`.env.example` нь хөгжүүлэлтийн анхдагч утгуудыг агуулна. Production-д нууцуудыг нууц хадгалалтаас оруулна.

| Хувьсагч | Production-ий утга | Тайлбар |
|---|---|---|
| `DJANGO_ENV` | `production` | `setup_demo`-г татгалзаж, удирдлагын самбараас орчны тэмдгийг хасна |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, хамгаалалттай cookie |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | Нууц хадгалалт | [Түлхүүрийн удирдлага](security-keys.md). Солихдоо өмнөх түлхүүрүүдийг `DJANGO_SECRET_KEY_FALLBACKS`-д хийнэ |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | Таслалаар тусгаарласан жагсаалт |
| `APP_URL` | `https://sis.example.ac.kr` | Мэйл дэх холбоос, тодорхойлолт баталгаажуулах QR код |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | Нууц хадгалалт | Алдвал хувийн мэдээллийг тайлах боломжгүй |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | Аппликейшн болон Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | `migrate`, `setup_install`, `audit_seal` болон `audit_prune` ашиглана. Нууц үгийг зөвхөн байршуулалт хийдэг сервер болон аудитын битүүмжлэл (`audit_seal`) ажиллуулдаг сервер дээр хадгална |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, [ачааллын тест](load-testing.md)-ийн утга, `60`, `2000`, `127.0.0.1` | `config/gunicorn.py` уншина. Анхдагч worker-ийн тоо нь CPU цөм тутамд 2 + 1. `GUNICORN_FORWARDED_ALLOW_IPS` нь зөвхөн gunicorn хэний `X-Forwarded-Proto`-д итгэхийг заана; клиентийн хаяг `TRUSTED_PROXY_COUNT`-оос гарна |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | [Ачааллын тест](load-testing.md)-д тогтоосон утга: `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` prepared statement-ийг асаана (RLS асуулгын төлөвлөлтийн зардлыг бууруулна); 0 бол унтраана |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Дотоод Redis | Broker болон үр дүн анхдагчаар `REDIS_URL` |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | Их сургуулийн SMTP relay | Урилга, хоёр шатлалт код, хичээл сонголт болон дүнгийн мэдэгдэл |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | Дотоод хаяг, `60` | |
| `PRIVATE_MEDIA_ROOT` | Нөөцлөгддөг диск | Хувийн файлын хадгалалт |
| `TRUSTED_PROXY_COUNT` | Ихэвчлэн `1` | Дээрх хэсэг |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` эсвэл түүнээс их | Дээрх хэсэг |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | HTTPS-ийг анх идэвхжүүлэхдээ богино HSTS-ээр (`300`) туршаад дараа нь нэмэгдүүлнэ |
| `SESSION_LIFETIME_MINUTES` | `120` | Нэвтэрсэн сессийн хугацаа |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, байгууллагын цагийн бүс | Серверийн цаг болон төлөвлөгдсөн ажлууд UTC-ээр, дэлгэцүүд байгууллагын цагийн бүсээр |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | Анхдагч утга | [LMS холболтын гарын авлага](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | Лог стандарт гаралт руу мөр тутамд нэг JSON объект хэлбэрээр бичигдэнэ |
| `VITE_DEV_MODE` | `false` | Production бүтээлтийн гаралтыг (`static/dist/manifest.json`) ашиглана |

## Байршуулах журам

1. Нөөцөлж ([нөөцлөлт ба сэргээлт](backup-restore.md)), `uv run manage.py audit_verify_chain`-ийг ажиллуулна.
2. Кодыг байршуулна: `git pull` (эсвэл шинэ image), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force`: миграц (`app_migrator` холболт руу автоматаар шилжинэ), шинэчилсэн зайлшгүй өгөгдөл (админы засварууд хадгалагдана), эрхийн каталогийн синхрончлол. Миграцыг дангаар нь ажиллуулахад `uv run manage.py migrate` ч мөн `app_migrator`-ийг автоматаар ашиглана. `app_runtime`-аар DDL ажиллуулах арга байхгүй.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. Production-ий Docker image хоёуланг нь бүтээх үед ажиллуулна.
5. Процессуудыг дахин эхлүүлнэ: gunicorn `reload` (HUP), Celery worker (TERM нь явагдаж буй ажлуудыг дуусгана; `acks_late`-ийн ачаар тасарсан ажил дахин ажиллана), Celery beat. Бүх серверт нийтдээ **яг нэг beat процесс** ажиллуулна. Хоёр байвал төлөвлөгдсөн ажил бүр хоёр удаа дараалалд орно (ажил тус бүрийн Redis түгжээ нь зэрэг ажиллахаас сэргийлэх боловч давхар дараалалд орохоос сэргийлэхгүй).
6. Шалгах: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (exit code 0), `GET /api/v1/health/` (`ok`), удирдлагын самбарт нэвтрэх, `uv run manage.py pdf_sample`. Flower дээр worker холбогдсон эсэхийг шалгана.

## Тогтмол шалгалт

| Давтамж | Ажил |
|---|---|
| Өдөр бүр (автомат) | `audit.seal`, `lms.reconcile`, хичээл сонголтын нөөцөлсөн суудлыг чөлөөлөх, хүлээлгийн жагсаалтын дэвшүүлэлт, өргөдлийн ноорогийн хугацаа дуусгах ([төлөвлөгдсөн ажлууд](scheduled-jobs.md)) |
| Долоо хоног бүр | `/api/v1/health/` болон `check --deploy`, Python, OS болон хамаарлын аюулгүй байдлын шинэчлэл (`pip-audit`), Flower дахь амжилтгүй ажлууд |
| Сар бүр | `media_prune_orphans --dry-run`, нөөцөөс сэргээх дадлага, `audit_verify_chain` |
| Улирал бүр | Үүргийн оноолтыг хянах (ажлаас гарсан эсвэл шилжсэн хүмүүс), хадгалах хугацаа нь өнгөрсөн аудитын бичлэгийг цэвэрлэх (`audit_prune`), хичээл сонголтын өмнө `LOGIN_RATE_LIMIT_PER_IP` болон worker-ийн тоог дахин шалгах |
