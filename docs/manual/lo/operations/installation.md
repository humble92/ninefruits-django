# ການຕິດຕັ້ງ

- ກຸ່ມເປົ້າໝາຍ: ຜູ້ປະຕິບັດງານ IT
- ກ່ຽວຂ້ອງ: [ເອກະສານອ້າງອີງຄຳສັ່ງ](commands.md), [ການຄຸ້ມຄອງກະແຈ](security-keys.md)

## 1. ຄວາມຕ້ອງການ

| ອົງປະກອບ | ເວີຊັນ | ໝາຍເຫດ |
|---|---|---|
| Python | 3.14 | ຕິດຕັ້ງ ແລະ ແລ່ນດ້ວຍ [uv](https://docs.astral.sh/uv/) (`uv sync`). ແພັກເກດລະບົບ: `gettext` (ຄອມໄພລ໌ການແປ), `libmagic` (ກວດຮູບແບບໄຟລ໌) |
| Node.js | 22 | build ຊັບພະຍາກອນໜ້າຈໍ (`npm ci && npm run build`). ເຊີບເວີນຳໃຊ້ຈິງຕ້ອງການພຽງຜົນການ build |
| PostgreSQL | 18 | ສ່ວນຂະຫຍາຍ `btree_gist`, `pg_trgm` (migration ຕິດຕັ້ງໃຫ້), ICU collation |
| Redis | 8 | cache, broker ແລະ ຜົນຂອງ Celery |
| Gotenberg | 8 | ສ້າງ PDF. ເປີດໃຫ້ເຂົ້າເຖິງສະເພາະເຄືອຂ່າຍພາຍໃນ |
| ເຊີບເວີອີເມວ | SMTP | ການຕັ້ງລະຫັດຜ່ານໃໝ່, ລະຫັດທາງອີເມວຂອງການຢືນຢັນສອງຂັ້ນຕອນ |
| ເວັບເຊີບເວີ | gunicorn + Nginx | `uv run gunicorn config.wsgi`. Nginx ໃຫ້ບໍລິການ `staticfiles/` ເອງ ແລະ ສົ່ງສ່ວນທີ່ເຫຼືອໃຫ້ gunicorn |
| worker ຂອງຄິວ | Celery worker | ແລ່ນ `uv run celery -A config worker` ຕະຫຼອດເວລາດ້ວຍຕົວຈັດການໂປຣເຊສ (systemd, supervisor) |
| ຕົວກຳນົດເວລາ | Celery beat | ແລ່ນ `uv run celery -A config beat` ພຽງເຄື່ອງດຽວ (DB scheduler, django-celery-beat) |
| ຕົວຕິດຕາມຄິວ | Flower (ທາງເລືອກ) | `uv run celery -A config flower`. ວາງໄວ້ຫຼັງ Nginx ໃຫ້ເຂົ້າໄດ້ສະເພາະຜູ້ທີ່ມີສິດ `ເບິ່ງຕົວຕິດຕາມຄິວ` |

## 2. ການກະກຽມຖານຂໍ້ມູນ

superuser ຂອງ DB ແລ່ນຄັ້ງດຽວ. ແອັບພລິເຄຊັນບໍ່ໃຊ້ superuser.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| ບົດບາດ | ຕົວແປສະພາບແວດລ້ອມ | ຈຸດປະສົງ |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | ແລ່ນແອັບພລິເຄຊັນ (ນຳໃຊ້ຄວາມປອດໄພລະດັບແຖວ, DDL ບໍ່ໄດ້) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | ສະເພາະ migration (`migrate` ໃຊ້ການເຊື່ອມຕໍ່ນີ້ອັດຕະໂນມັດ) |
| `app_reporting` | (ຕັ້ງໃນເຄື່ອງມື BI) | ອ່ານ schema `reporting` |

ໃນສະພາບແວດລ້ອມພັດທະນາ Docker Compose, `docker/pgsql/20-create-app-roles.sh` ເຮັດວຽກດຽວກັນເມື່ອ container `pgsql` ເລີ່ມເທື່ອທຳອິດ (ສ້າງບົດບາດ, ກະກຽມ `ninefruits` ແລະ DB ທົດສອບ).

## 3. ການຕັ້ງຄ່າສະພາບແວດລ້ອມ

ສຳເນົາ `.env.example` ເປັນ `.env` ແລ້ວໃສ່ຄ່າ (ໃນການນຳໃຊ້ຈິງ ໃຫ້ໃສ່ເປັນຕົວແປສະພາບແວດລ້ອມ ຫຼື ຈາກບ່ອນເກັບຄວາມລັບ). ຄ່າທີ່ຕ້ອງປ່ຽນ:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. ເກັບຮັກສາຕາມ [ການຄຸ້ມຄອງກະແຈ](security-keys.md).
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **ຖ້າເຮັດເສຍ ຈະກູ້ຄືນຂໍ້ມູນສ່ວນບຸກຄົນທີ່ເຂົ້າລະຫັດແລ້ວບໍ່ໄດ້.** ເກັບແຍກໄວ້ຕາມ [ການຄຸ້ມຄອງກະແຈ](security-keys.md).
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `INSTITUTION_TIMEZONE`: ຄ່າເລີ່ມຕົ້ນຂອງເຂດເວລາສະຖາບັນໃນການຕິດຕັ້ງຄັ້ງທຳອິດ (ຕົວຢ່າງ `Asia/Vientiane`)

## 4. ການຕິດຕັ້ງ

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py migrate                    # migration ຂອງ schema ແລະ ຂໍ້ມູນ ຜ່ານການເຊື່ອມຕໍ່ app_migrator
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py security_sync_permissions  # ເຮັດໃຫ້ລາຍການສິດໃນ DB ກົງກັບໂຄດ
echo "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator \
    --email=admin@example.edu.la --name="ຜູ້ບໍລິຫານ" --password-stdin
```

`createsuperuser` ຂອງ Django ຖືກປິດໃຊ້ງານ. ຜູ້ບໍລິຫານຄົນທຳອິດສ້າງໄດ້ດ້ວຍ `security_create_administrator` ເທົ່ານັ້ນ ([ເອກະສານອ້າງອີງຄຳສັ່ງ](commands.md)). ຄຳສັ່ງນີ້ຕ້ອງມີບົດບາດຜູ້ບໍລິຫານລະບົບ (ຂໍ້ມູນທີ່ຈຳເປັນ) ແລະ ຖ້າບໍ່ມີ ຈະບອກວ່າຕ້ອງແລ່ນຫຍັງກ່ອນ. ຕັ້ງແຕ່ Phase 1, `setup_install` ຈະດຳເນີນການ migration, ຂໍ້ມູນທີ່ຈຳເປັນ, ການຕັ້ງຄ່າເລີ່ມຕົ້ນຂອງສະຖາບັນ, ໂປຣໄຟລ໌ການຕິດຕັ້ງ ແລະ ຜູ້ບໍລິຫານຄົນທຳອິດຕາມລຳດັບ.

ຫຼັງຈາກຕິດຕັ້ງ ຜູ້ບໍລິຫານວຽກງານປ້ອນຂໍ້ມູນອ້າງອີງຕາມ [ຄູ່ມືຜູ້ບໍລິຫານບົດທີ 5 ລຳດັບການຕັ້ງຄ່າເບື້ອງຕົ້ນ](../admin/05-institution-setup.md).

### Docker Compose (ພັດທະນາ)

```bash
cp .env.example .env
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py migrate
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py security_sync_permissions
docker compose exec app uv run manage.py security_create_administrator --email=admin@example.test --name="ຜູ້ບໍລິຫານ"
```

| ບໍລິການ | ທີ່ຢູ່ |
|---|---|
| ແອັບພລິເຄຊັນ | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (ກ່ອງອີເມວສຳລັບພັດທະນາ) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite dev server (ທາງເລືອກ, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

## 5. ການກວດຫຼັງຕິດຕັ້ງ

1. ເຂົ້າສູ່ລະບົບເປັນຜູ້ບໍລິຫານຄົນທຳອິດທີ່ `/accounts/login/`. `/admin/` ຕ້ອງເປີດໄດ້ ແລະ ເມນູດ້ານຊ້າຍຕ້ອງມີ **ຜູ້ໃຊ້ ແລະ ສິດເຂົ້າເຖິງ**, **ການກວດສອບ**, **ການຕັ້ງຄ່າ**.
2. ກຳນົດນະໂຍບາຍການຢືນຢັນສອງຂັ້ນຕອນທີ່ **ການຕັ້ງຄ່າ > ຄວາມປອດໄພ** ໃນໜ້າບໍລິຫານ.
3. ລົງທະບຽນການຢືນຢັນສອງຂັ້ນຕອນຂອງຜູ້ບໍລິຫານເອງ (ພອດທໍ **ຄວາມປອດໄພ**, `/portal/security/`).
4. ກວດບໍລິການ PDF ດ້ວຍ `uv run manage.py pdf_sample`.
5. ກວດວ່າວຽກການຕິດຕັ້ງຖືກບັນທຶກເປັນ `system:command:...` ທີ່ **ການກວດສອບ > ບັນທຶກການປ່ຽນແປງຂໍ້ມູນ** ໃນໜ້າບໍລິຫານ.
6. ກວດວ່າ `uv run manage.py check --deploy` ບໍ່ມີຄຳເຕືອນການຕັ້ງຄ່າສຳລັບການນຳໃຊ້ຈິງ.

## 6. ການອັບເດດ

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py migrate
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # ເລີ່ມ web worker ໃໝ່ດ້ວຍໂຄດໃໝ່
sudo systemctl restart ninefruits-celery ninefruits-beat
```

ຕັ້ງແຕ່ Phase 1 ໃຫ້ແລ່ນ `setup_install --force` (migration, ຂໍ້ມູນທີ່ຈຳເປັນ, ການຊິງຄ໌ສິດ) ແທນ `migrate`. ປ່ຽນຊື່ບໍລິການໃຫ້ກົງກັບການຕິດຕັ້ງຂອງທ່ານ.
