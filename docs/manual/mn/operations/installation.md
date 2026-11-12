# Суулгалт

- Зориулалт: МТ-ийн ашиглалтын ажилтнууд
- Холбогдох: [командын лавлах](commands.md), [түлхүүрийн удирдлага](security-keys.md), [байршуулалтын хяналтын хуудас](deployment-checklist.md)

## 1. Шаардлага

| Бүрэлдэхүүн | Хувилбар | Тайлбар |
|---|---|---|
| Python | 3.14 | [uv](https://docs.astral.sh/uv/)-ээр суулгаж ажиллуулна (`uv sync`). Системийн багцууд: `gettext` (орчуулга хөрвүүлэх), `libmagic` (файлын төрөл тодорхойлох) |
| Node.js | 22 | Дэлгэцийн asset-уудыг бүтээнэ (`npm ci && npm run build`). Production серверт зөвхөн бүтээлтийн гаралт хэрэгтэй |
| PostgreSQL | 18 | `btree_gist`, `pg_trgm` өргөтгөл (миграцаар суулгагдана), ICU collation |
| Redis | 8 | Кэш, сесс, Celery broker ба үр дүн |
| Gotenberg | 8 | PDF үүсгэх. Зөвхөн дотоод сүлжээнд нээлттэй |
| Мэйл сервер | SMTP | Нууц үг сэргээх, хоёр шатлалт баталгаажуулалтын и-мэйл код, урилга, мэдэгдэл |
| Веб сервер | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`. Nginx `staticfiles/`-ийг өөрөө түгээж, бусдыг gunicorn руу дамжуулна |
| Дарааллын worker | Celery worker | `uv run celery -A config worker`-ийг процесс менежерээр (systemd, supervisor) тасралтгүй ажиллуулна |
| Төлөвлөгч | Celery beat | `uv run celery -A config beat`-ийг **яг нэг** машин дээр ажиллуулна (өгөгдлийн сангийн төлөвлөгч, django-celery-beat) |
| Дарааллын монитор | Flower (сонголтоор) | `uv run celery -A config flower`. Дотоод сүлжээнд эсвэл Nginx-ийн хандалтын хязгаарлалтын (эсвэл Flower-ийн `--basic-auth`) ард байлгана; хэзээ ч ил гаргахгүй |

## 2. Өгөгдлийн санг бэлтгэх

Өгөгдлийн сангийн superuser-ээр нэг удаа ажиллуулна. Аппликейшн superuser-ийг хэзээ ч ашигладаггүй.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| Роль | Орчны хувьсагч | Зориулалт |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | Аппликейшныг ажиллуулах (мөрийн түвшний хамгаалалт үйлчилнэ, DDL байхгүй) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | Зөвхөн миграц, аудитын битүүмжлэл ба цэвэрлэлт (`migrate` энэ холболтыг автоматаар ашиглана) |
| `app_reporting` | (BI хэрэгсэлд тохируулна) | `reporting` схемийг унших |

Docker Compose хөгжүүлэлтийн орчинд `pgsql` контейнер анх эхлэхэд `docker/pgsql/20-create-app-roles.sh` мөн адил үйлдлийг (роль, `ninefruits` болон тестийн өгөгдлийн сангууд) гүйцэтгэнэ.

## 3. Орчны тохиргоо

`.env.example`-ийг `.env` болгон хуулж утгуудыг бөглөнө (production-д орчны хувьсагч эсвэл нууц хадгалалтаас өгнө). Заавал өөрчлөх утгууд:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. [Түлхүүрийн удирдлага](security-keys.md)-д заасны дагуу хадгална.
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **Эдгээрийг алдвал шифрлэгдсэн хувийн мэдээллийг сэргээх боломжгүй.** [Түлхүүрийн удирдлага](security-keys.md)-д заасны дагуу тусад нь хадгална.
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: аппликейшны өмнөх reverse proxy-ийн тоо (ганц Nginx бол `1`). [Байршуулалтын хяналтын хуудас](deployment-checklist.md#прокси-ба-клиентийн-хаяг)-ыг үзнэ үү
- `INSTITUTION_TIMEZONE`: анхны суулгалтын үеийн байгууллагын үндсэн цагийн бүс (жишээ нь `Asia/Seoul`)

Production-ийн орчны хувьсагчийн бүрэн жагсаалт [байршуулалтын хяналтын хуудас](deployment-checklist.md#орчны-хувьсагчид)-т байна.

## 4. Суулгах

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` дараах дарааллаар ажиллана: миграц (`app_migrator` холболтоор), зайлшгүй өгөгдөл (үүргийн загвар ба эрхийн синхрончлол, улс, хэл, лавлах төрөл, бүтцийн нэгжийн төрөл, шилжилт хөдөлгөөний төрөл, хичээл сонголтын дүрмийн багц), байгууллагын анхдагч утга (анхдагч хэл, цагийн бүс, байгууллагын нэр), дүнгийн шкалыг тогтоох, суулгалтын профайл болон анхны админ. Байршуулалтын скриптэд `--force` болон сонголтуудтай ажиллуулна; админы нууц үгийг стандарт оролтоос уншина.

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

Суулгалтын профайл (`--profile=`, нэгээс олон удаа өгч болно)

| Түлхүүр | Агуулга |
|---|---|
| `korean-university` | Хавар/зун/намар/өвлийн улирлын төрөл, 4.5 дүнгийн шкал, хичээлийн ангилал, 09:00-оос эхэлсэн пар, танхимын төрөл, элсэлтийн төрөл ба өргөдлийн баримт, анхдагч хичээлийн үнэлгээний маягт, дөрвөн хэлний загвартай тодорхойлолтын төрлүүд |
| `yust-legacy` | `korean-university`-ийн бүх зүйл, нэмээд элссэн он болон сувилахуйн кредитийн хязгаар, хязгаарт тооцохгүй кредит банкны хичээлүүд, 4.3 дүнгийн шкал ба түүний дүнгийн бодлого |

Профайлгүй бол эдгээрийг удирдлагын самбарт оруулна. Дараа нь профайлыг дахин хэрэглэхэд админуудын өөрчилсөн утгууд хадгалагдана. Дүнгийн шкалыг нэг тогтоосны дараа өөрчлөх боломжгүй (дүн болон голч дүнг тэр шкалаар хадгалдаг).

Django-гийн `createsuperuser` идэвхгүй. Анхны админыг зөвхөн `setup_install` эсвэл `security_create_administrator`-оор үүсгэнэ ([командын лавлах](commands.md)).

Суулгалтын дараа бизнесийн админ [админы гарын авлагын 5-р бүлэг, анхны тохиргооны дараалал](../admin/05-institution-setup.md)-ын дагуу лавлах мэдээллийг оруулна. Серверийн процессуудыг (gunicorn, Celery worker, beat) [байршуулалтын хяналтын хуудас](deployment-checklist.md) болон [төлөвлөгдсөн ажлууд](scheduled-jobs.md)-д заасны дагуу бүртгэнэ.

### Docker Compose (хөгжүүлэлт)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| Үйлчилгээ | Хаяг |
|---|---|
| Аппликейшн | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (хөгжүүлэлтийн шуудангийн хайрцаг) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite dev сервер (сонголтоор, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

Production-ийн image нь `Dockerfile`-ийн `production` target (анхдагч). Бүтээх үед `compilemessages` болон `collectstatic`-ийг ажиллуулж, gunicorn-ийг эхлүүлнэ. Ижил image worker болон beat-ийг ажиллуулна (`uv run --no-sync celery -A config worker|beat`).

## 5. Суулгалтыг шалгах

1. `/accounts/login/` хаягаар анхны админаар нэвтэрнэ. `/admin/` нээгдэж, хажуугийн цэсэнд **Хэрэглэгч ба эрх**, **Аудит**, **Тохиргоо** харагдана.
2. Удирдлагын самбарын **Тохиргоо > Аюулгүй байдал** хэсэгт хоёр шатлалт баталгаажуулалтын бодлогыг тохируулна.
3. Админы хоёр шатлалт баталгаажуулалтыг бүртгүүлнэ (порталын **Аюулгүй байдал**, `/portal/security/`).
4. `uv run manage.py pdf_sample`-аар PDF үйлчилгээг шалгана.
5. Удирдлагын самбарын **Аудит > Өгөгдлийн өөрчлөлтүүд** хэсэгт суулгалт `system:command:setup_install` гэж харагдаж буйг шалгана.
6. `uv run manage.py check --deploy` production-ийн анхааруулга мэдээлэхгүй, `GET /api/v1/health/` `{"status": "ok"}` гэж хариулж буйг шалгана (beat нэг минут ажилласан байх ёстой).

## 6. Шинэчлэх

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

Үйлчилгээний нэрийг өөрийн суулгалтад тааруулна. Шинэчлэлийн өмнөх ба дараах нөөцлөлт, шалгалтыг [байршуулалтын хяналтын хуудас](deployment-checklist.md#байршуулах-журам)-ын дагуу хийнэ.
