# Joriy etish nazorat roʻyxati, gunicorn va Python sozlamalari

- Kim uchun: IT operatorlari
- Bogʻliq: [oʻrnatish](installation.md), [kalitlarni boshqarish](security-keys.md), [rejalashtirilgan vazifalar](scheduled-jobs.md), [yuklama testi](load-testing.md)

## Python va bogʻliqliklar

- **Python 3.14** ning eng soʻnggi patch relizidan foydalaning. Konteyner yoki server obrazlarini yigʻishda Python patch versiyasini qotirib qoʻymang; eng soʻnggisini oling (`Dockerfile` dagi `python:3.14-slim`).
- Python bogʻliqliklari `uv.lock` da qotirilgan. Production oʻrnatishlari har doim `uv sync --frozen --no-dev` dan foydalanadi (lock fayli mos kelmasa, xato beradi). Ishlab chiqish vositalari (pytest, ruff, mypy, Playwright) hech qachon production ga tushmaydi.
- Django xavfsizlik relizini eʼlon qilganda, `uv lock --upgrade-package django` bilan yangilang, testlarni bajaring va joriy eting. Bogʻliqliklar zaifliklarini CI dagidek tekshiring: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`.
- `uv run manage.py check --deploy` production sozlamalari (`DEBUG`, HTTPS, cookie fayllari, HSTS, maxfiy kalit uzunligi) haqida ogohlantiradi. Har bir joriy etishda ogohlantirishlar soni nol boʻlishi kerak.

## gunicorn va Nginx

| Band | Qiymat | Sabab |
|---|---|---|
| gunicorn ni ishga tushirish | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, sync workerlar. Workerlar soni va ulanishlar pooli hajmi muhit oʻzgaruvchilaridan olinadi; asoslash [yuklama testi](load-testing.md) da |
| gunicorn bind | `127.0.0.1:8000` yoki Unix soketi | gunicorn ni hech qachon toʻgʻridan-toʻgʻri ochmang; uni har doim Nginx ortiga qoʻying |
| Workerlarni qayta ishga tushirish | Joriy etishda `HUP` (systemd `reload`) | Bajarilayotgan soʻrovlarni tugatadi va workerlarni yangi kod bilan almashtiradi |
| MB ulanishlari | `DB_POOL=true` bilan har bir worker uchun psycopg ulanishlar pooli (`DB_POOL_MIN`, `DB_POOL_MAX`) | Workerlar × `DB_POOL_MAX` + Celery ulanishlari PostgreSQL ning `max_connections` qiymatidan kam boʻlishi kerak. Poolga qaytarilgan ulanishning MB sessiyasi ijrochisi tozalanadi (`ninefruits.core.pool.reset_connection`) |
| Nginx `client_max_body_size` | `32m` | Qabul hujjatlari, imtihon tasdiqlovchi hujjatlari va suratlarni yuklash uchun yuqori chegara (ilovadagi 5MB va 2MB tekshiruvidan yuqori zaxira) |
| Nginx statik fayllari | `location /static/ { alias <repository>/staticfiles/; }` | `collectstatic` natijasini Nginx oʻzi uzatadi |
| Shaxsiy fayllar | `PRIVATE_MEDIA_ROOT` (standart `storage/private`) ni Nginx da **hech qachon ulamang** | Suratlar, ariza hujjatlari va maʼlumotnoma PDF fayllari faqat ruxsat tekshiriladigan view lar orqali yuklab olinadi |
| Nginx sarlavhalari | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, ixtiyoriy ravishda `X-Request-Id $request_id` | Mijoz manzili, HTTPS ni aniqlash, soʻrovlar boʻyicha kuzatuv |
| Gotenberg, Redis, PostgreSQL | Faqat ichki manzillar | Hech qachon tashqariga ochilmaydi |

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

### Proksilar va mijoz manzili

Kirish cheklovlari, API tezlik cheklovlari va audit yozuvlaridagi IP manzillar `ninefruits.core.http.client_ip` aniqlagan mijoz manzilidan foydalanadi.

- `TRUSTED_PROXY_COUNT`: ilova oldidagi `X-Forwarded-For` ga qoʻshadigan teskari proksilar soni. Bitta Nginx uchun `1`, yuklama muvozanatlagichi va Nginx uchun `2`. `0` (standart) `REMOTE_ADDR` dan foydalanadi. Oʻngdan shuncha oʻrindagi yozuv mijoz manzili hisoblanadi; chaproqdagi yozuvlarga (mijoz yuborganlariga) hech qachon ishonilmaydi.
- **Agar qiymat haqiqiy proksilar sonidan kam boʻlsa**, har bir foydalanuvchi Nginx manzilidan kelgandek koʻrinadi va kirish cheklovi butun kampusga birdaniga qoʻllanadi. **Agar koʻp boʻlsa**, ilova mijoz yuborgan `X-Forwarded-For` ga ishonadi va cheklovlarni chetlab oʻtish mumkin boʻladi. Joriy etgandan keyin boshqaruv panelidagi **Audit > Xavfsizlik hodisalari** dagi IP manzillar haqiqiy foydalanuvchi manzillari ekanini tekshiring.
- `LOGIN_RATE_LIMIT_PER_IP`: har bir mijoz manzili uchun kirish urinishlari (django-allauth, standart `30/m/ip`). Asl tizimda bunday cheklov yoʻq edi. Agar butun kampus bitta NAT manzili orqali chiqsa, bu fanlarga yozilishning birinchi ertalabi uchun juda kam; uni oshiring (masalan, `300/m/ip`). Boʻsh qiymat manzil boʻyicha cheklov yoʻqligini bildiradi (asl tizimdagidek). Hisob boʻyicha muvaffaqiyatsiz urinishlar cheklovi (daqiqasiga 5) va hisobni bloklash bu qiymatdan qatʼi nazar amal qiladi.

## Muhit oʻzgaruvchilari

`.env.example` ishlab chiqish uchun standart qiymatlarni oʻz ichiga oladi. Production da maxfiy qiymatlarni maxfiy maʼlumotlar omboridan kiriting.

| Oʻzgaruvchi | Production qiymati | Izohlar |
|---|---|---|
| `DJANGO_ENV` | `production` | `setup_demo` ni rad etadi va boshqaruv panelidan muhit belgisini olib tashlaydi |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, xavfsiz cookie fayllari |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | Maxfiy maʼlumotlar ombori | [Kalitlarni boshqarish](security-keys.md). Almashtirishda oldingi kalitlar `DJANGO_SECRET_KEY_FALLBACKS` ga oʻtadi |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | Vergul bilan ajratilgan roʻyxatlar |
| `APP_URL` | `https://sis.example.ac.kr` | Xatlardagi havolalar, maʼlumotnomalarni tekshirish QR kodlari |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | Maxfiy maʼlumotlar ombori | Yoʻqolsa, shaxsiy maʼlumotlarni shifrdan chiqarib boʻlmaydi |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | Ilova va Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | `migrate`, `setup_install`, `audit_seal` va `audit_prune` foydalanadi. Parolni faqat joriy etishlarni bajaradigan server va audit muhrlashni (`audit_seal`) bajaradigan serverda saqlang |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, [yuklama testi](load-testing.md) dagi qiymat, `60`, `2000`, `127.0.0.1` | `config/gunicorn.py` oʻqiydi. Standart workerlar soni har bir CPU yadrosiga 2 + 1. `GUNICORN_FORWARDED_ALLOW_IPS` faqat gunicorn kimning `X-Forwarded-Proto` siga ishonishini bildiradi; mijoz manzili `TRUSTED_PROXY_COUNT` dan olinadi |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | [Yuklama testi](load-testing.md) da belgilangan qiymatlar: `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` tayyorlangan soʻrovlarni yoqadi (RLS soʻrovlarini rejalashtirish xarajatini kamaytiradi); 0 ularni oʻchiradi |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Ichki Redis | Broker va natijalar standart holatda `REDIS_URL` dan foydalanadi |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | Universitetning SMTP relesi | Taklifnomalar, ikki bosqichli autentifikatsiya kodlari, fanlarga yozilish va baholar haqidagi bildirishnomalar |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | Ichki manzil, `60` | |
| `PRIVATE_MEDIA_ROOT` | Zaxiralanadigan disk | Shaxsiy fayllar ombori |
| `TRUSTED_PROXY_COUNT` | Odatda `1` | Yuqoridagi boʻlim |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` yoki undan yuqori | Yuqoridagi boʻlim |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | HTTPS ni birinchi marta yoqishda, oshirishdan oldin qisqa HSTS (`300`) ni sinab koʻring |
| `SESSION_LIFETIME_MINUTES` | `120` | Tizimga kirilgan sessiyaning amal qilish muddati |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, muassasa vaqt mintaqasi | Server vaqtlari va rejalashtirilgan vazifalar UTC da, ekranlar muassasa vaqt mintaqasida |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | Standart qiymatlar | [LMS integratsiyasi qoʻllanmasi](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | Jurnallar standart chiqishga har bir qatorda bitta JSON obyekt sifatida yoziladi |
| `VITE_DEV_MODE` | `false` | Production yigʻish natijasidan (`static/dist/manifest.json`) foydalanadi |

## Joriy etish tartibi

1. Zaxira nusxa oling ([zaxiralash va tiklash](backup-restore.md)) va `uv run manage.py audit_verify_chain` ni bajaring.
2. Kodni joriy eting: `git pull` (yoki yangi obraz), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force`: migratsiyalar (avtomatik ravishda `app_migrator` ulanishiga oʻtadi), yangilangan zaruriy maʼlumotlar (administrator oʻzgartirishlari saqlanadi), ruxsatlar katalogini sinxronlash. Migratsiyalarni alohida bajarishda `uv run manage.py migrate` ham avtomatik ravishda `app_migrator` dan foydalanadi. DDL ni `app_runtime` sifatida bajarishning imkoni yoʻq.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. Production Docker obrazi ikkalasini ham yigʻish vaqtida bajaradi.
5. Jarayonlarni qayta ishga tushiring: gunicorn `reload` (HUP), Celery worker (TERM bajarilayotgan vazifalarni tugatishga imkon beradi; `acks_late` bilan uzilgan vazifa qayta bajariladi), Celery beat. Barcha serverlarda **aynan bitta beat jarayoni** ishlasin. Ikkita boʻlsa, har bir rejalashtirilgan vazifa navbatga ikki marta qoʻyiladi (har bir vazifaning Redis qulfi takroriy navbatga qoʻyishning emas, bir vaqtda bajarilishning oldini oladi).
6. Tekshiring: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (chiqish kodi 0), `GET /api/v1/health/` (`ok`), boshqaruv paneliga kirish, `uv run manage.py pdf_sample`. Flower da worker ulanganini tekshiring.

## Muntazam tekshiruvlar

| Davriylik | Vazifa |
|---|---|
| Har kuni (avtomatik) | `audit.seal`, `lms.reconcile`, ajratilgan oʻrinlarni boʻshatish, kutish roʻyxatidan oʻtkazish, ariza qoralamalari muddatini tugatish ([rejalashtirilgan vazifalar](scheduled-jobs.md)) |
| Har hafta | `/api/v1/health/` va `check --deploy`, Python, OT va bogʻliqliklar xavfsizlik yangilanishlari (`pip-audit`), Flower dagi muvaffaqiyatsiz vazifalar |
| Har oy | `media_prune_orphans --dry-run`, zaxiradan tiklash mashqi, `audit_verify_chain` |
| Har semestr | Rol tayinlashlarini koʻrib chiqish (ketgan yoki boshqa joyga oʻtgan shaxslar), saqlash muddati oʻtgan audit yozuvlarini tozalash (`audit_prune`), fanlarga yozilishdan oldin `LOGIN_RATE_LIMIT_PER_IP` va workerlar sonini qayta tekshirish |
