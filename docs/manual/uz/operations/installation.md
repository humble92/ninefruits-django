# Oʻrnatish

- Kim uchun: IT operatorlari
- Bogʻliq: [buyruqlar maʼlumotnomasi](commands.md), [kalitlarni boshqarish](security-keys.md), [joriy etish nazorat roʻyxati](deployment-checklist.md)

## 1. Talablar

| Komponent | Versiya | Izohlar |
|---|---|---|
| Python | 3.14 | [uv](https://docs.astral.sh/uv/) bilan oʻrnatiladi va ishga tushiriladi (`uv sync`). Tizim paketlari: `gettext` (tarjimalarni kompilyatsiya qilish), `libmagic` (fayl turini aniqlash) |
| Node.js | 22 | Ekran resurslarini yigʻadi (`npm ci && npm run build`). Production serverlarga faqat yigʻish natijasi kerak |
| PostgreSQL | 18 | `btree_gist`, `pg_trgm` kengaytmalari (migratsiyalar oʻrnatadi), ICU collation lari |
| Redis | 8 | Kesh, sessiyalar, Celery brokeri va natijalari |
| Gotenberg | 8 | PDF yaratish. Faqat ichki tarmoqda oching |
| Pochta serveri | SMTP | Parolni tiklash, e-pochta orqali ikki bosqichli autentifikatsiya kodlari, taklifnomalar, bildirishnomalar |
| Veb-server | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`. Nginx `staticfiles/` ni oʻzi uzatadi, qolgan hammasini gunicorn ga yuboradi |
| Navbat ishlovchisi | Celery worker | `uv run celery -A config worker` ni jarayonlar menejeri (systemd, supervisor) ostida doimiy ishlab turishini taʼminlang |
| Rejalashtiruvchi | Celery beat | `uv run celery -A config beat` ni **aynan bitta** mashinada ishga tushiring (maʼlumotlar bazasi rejalashtiruvchisi, django-celery-beat) |
| Navbat monitori | Flower (ixtiyoriy) | `uv run celery -A config flower`. Uni ichki tarmoqda yoki Nginx kirish cheklovi ortida (yoki Flower ning `--basic-auth` i bilan) saqlang; hech qachon tashqariga ochmang |

## 2. Maʼlumotlar bazasini tayyorlash

Maʼlumotlar bazasi superfoydalanuvchisi sifatida bir marta bajaring. Ilova hech qachon superfoydalanuvchidan foydalanmaydi.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| Rol | Muhit oʻzgaruvchilari | Vazifasi |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | Ilovani ishga tushirish (qator darajasidagi xavfsizlik qoʻllanadi, DDL yoʻq) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | Faqat migratsiyalar, audit muhrlash va tozalash (`migrate` bu ulanishdan avtomatik foydalanadi) |
| `app_reporting` | (BI vositalarida sozlanadi) | `reporting` sxemasini oʻqish |

Docker Compose ishlab chiqish muhitida `docker/pgsql/20-create-app-roles.sh` `pgsql` konteyneri birinchi marta ishga tushganda xuddi shu ishni bajaradi (rollar, `ninefruits` va test bazalari).

## 3. Muhitni sozlash

`.env.example` ni `.env` ga nusxalang va qiymatlarni toʻldiring (production da ularni muhit oʻzgaruvchilari sifatida yoki maxfiy maʼlumotlar omboridan bering). Oʻzgartirilishi shart boʻlgan qiymatlar:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. Uni [kalitlarni boshqarish](security-keys.md) da tavsiflanganidek saqlang.
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **Ular yoʻqolsa, shifrlangan shaxsiy maʼlumotlarni tiklab boʻlmaydi.** Ularni [kalitlarni boshqarish](security-keys.md) da tavsiflanganidek alohida saqlang.
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: ilova oldidagi teskari proksilar soni (bitta Nginx uchun `1`). [Joriy etish nazorat roʻyxati](deployment-checklist.md#proksilar-va-mijoz-manzili) ga qarang
- `INSTITUTION_TIMEZONE`: birinchi oʻrnatish uchun muassasaning standart vaqt mintaqasi (masalan, `Asia/Seoul`)

Production muhit oʻzgaruvchilarining toʻliq roʻyxati [joriy etish nazorat roʻyxati](deployment-checklist.md#muhit-ozgaruvchilari) da.

## 4. Oʻrnatish

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` quyidagilarni ketma-ket bajaradi: migratsiyalar (`app_migrator` ulanishi orqali), zaruriy maʼlumotlar (rol shablonlari va ruxsatlarni sinxronlash, mamlakatlar, tillar, kod turlari, tashkiliy birlik turlari, maqom oʻzgarishi turlari, fanlarga yozilish qoidalari toʻplamlari), muassasaning standart qiymatlari (standart til, vaqt mintaqasi, muassasa nomi), baholash shkalasini belgilash, oʻrnatish profillari va birinchi administrator. Joriy etish skriptlarida uni `--force` va parametrlar bilan ishga tushiring; administrator paroli standart kirishdan oʻqiladi.

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

Oʻrnatish profillari (`--profile=`, bir necha marta berilishi mumkin)

| Kalit | Mazmuni |
|---|---|
| `korean-university` | Bahorgi/yozgi/kuzgi/qishki semestr turlari, 4.5 baholash shkalasi, fan toifalari, 09:00 dan boshlanadigan paralar, auditoriya turlari, qabul turlari va ariza hujjatlari, standart fan soʻrovnomasi shakli, toʻrt tildagi shablonlari bilan maʼlumotnoma turlari |
| `yust-legacy` | `korean-university` dagi hammasi, shuningdek qabul yili va hamshiralik boʻyicha kredit chegaralari, chegaradan tashqari kredit banki fanlari, 4.3 baholash shkalasi va uning baholash siyosati |

Profilsiz bularni boshqaruv panelida kiriting. Profilni keyinroq qayta qoʻllash administratorlar oʻzgartirgan qiymatlarni saqlaydi. Baholash shkalasini bir marta belgilangandan keyin oʻzgartirib boʻlmaydi (baholar va GPA shu shkalada saqlanadi).

Djangoning `createsuperuser` buyrugʻi oʻchirilgan. Birinchi administrator faqat `setup_install` yoki `security_create_administrator` bilan yaratiladi ([buyruqlar maʼlumotnomasi](commands.md)).

Oʻrnatishdan keyin biznes administratorlari asosiy maʼlumotlarni [administrator qoʻllanmasining 5-bobi, dastlabki sozlash tartibi](../admin/05-institution-setup.md) boʻyicha kiritadi. Server jarayonlarini (gunicorn, Celery worker, beat) [joriy etish nazorat roʻyxati](deployment-checklist.md) va [rejalashtirilgan vazifalar](scheduled-jobs.md) da tavsiflanganidek roʻyxatdan oʻtkazing.

### Docker Compose (ishlab chiqish)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| Xizmat | Manzil |
|---|---|
| Ilova | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (ishlab chiqish pochta qutisi) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite dev server (ixtiyoriy, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

Production obrazi `Dockerfile` ning `production` maqsadi (standart). U yigʻish vaqtida `compilemessages` va `collectstatic` ni bajaradi va gunicorn ni ishga tushiradi. Xuddi shu obraz worker va beat ni ham ishga tushiradi (`uv run --no-sync celery -A config worker|beat`).

## 5. Oʻrnatishni tekshirish

1. `/accounts/login/` da birinchi administrator sifatida tizimga kiring. `/admin/` ochiladi va yon panelda **Foydalanuvchilar va kirish**, **Audit** va **Sozlamalar** koʻrinadi.
2. Boshqaruv panelida **Sozlamalar > Xavfsizlik** boʻlimida ikki bosqichli autentifikatsiya siyosatini belgilang.
3. Administrator uchun ikki bosqichli autentifikatsiyani yoqing (portaldagi **Xavfsizlik**, `/portal/security/`).
4. PDF xizmatini `uv run manage.py pdf_sample` bilan tekshiring.
5. Boshqaruv panelida **Audit > Maʼlumot oʻzgarishlari** oʻrnatishni `system:command:setup_install` sifatida koʻrsatishini tekshiring.
6. `uv run manage.py check --deploy` production ogohlantirishlarini koʻrsatmasligini va `GET /api/v1/health/` `{"status": "ok"}` deb javob berishini tekshiring (beat bir daqiqa ishlagan boʻlishi kerak).

## 6. Yangilash

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

Xizmat nomlarini oʻz oʻrnatmangizga moslang. Yangilash atrofidagi zaxiralash va tekshiruvlar uchun [joriy etish nazorat roʻyxati](deployment-checklist.md#joriy-etish-tartibi) ga amal qiling.
