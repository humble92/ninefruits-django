# Ninefruits — ລະບົບບໍລິຫານການສຶກສາຂອງມະຫາວິທະຍາໄລ (Django)

**언어 / Languages / 语言 / ພາສາ**

| ພາສາ | README | ຄູ່ມື |
|---|---|---|
| 한국어 | [README.md](README.md) | [docs/manual/ko/](docs/manual/ko/README.md) |
| English | [README.en.md](README.en.md) | [docs/manual/en/](docs/manual/en/README.md) |
| 简体中文 | [README.zh_Hans.md](README.zh_Hans.md) | [docs/manual/zh_Hans/](docs/manual/zh_Hans/README.md) |
| ລາວ | [README.lo.md](README.lo.md) (ເອກະສານນີ້) | [docs/manual/lo/](docs/manual/lo/README.md) |

Ninefruits ແມ່ນລະບົບບໍລິຫານການສຶກສາ (Student Information System) ທີ່ສາມາດຕິດຕັ້ງ ແລະ ໃຊ້ໄດ້ໃນຫຼາຍມະຫາວິທະຍາໄລ. repository ນີ້ກຳລັງຍ້າຍໜ້າທີ່ທັງໝົດຂອງ [Ninefruits](https://github.com/humble92/ninefruits-laravel) (Laravel 13) v1.0.0 ມາເປັນ Python 3.14 / Django 6.1 / PostgreSQL 18. ມັນຄວບຄຸມການສະໝັກເຂົ້າຮຽນ, ບັນທຶກນັກສຶກສາ, ຫຼັກສູດ ແລະ ກຸ່ມຮຽນ, ການລົງທະບຽນຮຽນ, ເກຣດ, ການປະເມີນການສອນ, ໃບຢັ້ງຢືນ, ການສອບເສັງພາສາ ແລະ ການສອບເສັງລວມ, ການເຂົ້າຮຽນ, ການພິຈາລະນາຈົບການສຶກສາ, ບົດລາຍງານ ແລະ ພື້ນຖານການເຊື່ອມຕໍ່ LMS. ໜ້າຈໍ ແລະ ເອກະສານຮອງຮັບພາສາເກົາຫຼີ, ອັງກິດ, ຈີນ ແລະ ລາວ.

- ແຜນການຍ້າຍ: [porting/porting-plan.md](porting/porting-plan.md) (Phase 0 ຫາ 13, ພາສາເກົາຫຼີ)
- ບັນທຶກການຍ້າຍ ແລະ ການຕັດສິນໃຈອອກແບບ: [porting/](porting/README.md)
- ຕົ້ນແບບ Django ກ່ອນໜ້ານີ້ຢູ່ໃນ branch `legacy-playground`, ໃຊ້ເປັນເອກະສານອ້າງອີງເທົ່ານັ້ນ.

## ໜ້າຈໍ

- **ໜ້າບໍລິຫານ** `/admin/`: ພະນັກງານດຳເນີນວຽກບັນທຶກນັກສຶກສາ, ວິຊາການ, ການຮັບເຂົ້າຮຽນ, ໃບຢັ້ງຢືນ, ການສອບເສັງ, ການຈົບການສຶກສາ ແລະ ບົດລາຍງານ (Django admin + unfold). ເມນູ ແລະ ປຸ່ມເປັນໄປຕາມສິດທີ່ໄດ້ຈາກບົດບາດ ແລະ ຂອບເຂດໜ່ວຍງານ ຫຼື ຫຼັກສູດ.
- **ພອດທໍ** `/portal/`: ໜ້າຈໍສຳລັບນັກສຶກສາ, ອາຈານ ແລະ ຜູ້ສະໝັກ (Django template + HTMX + Alpine.js + Tailwind CSS). ເມນູສະແດງຕາມສະຖານະ (ນັກສຶກສາ, ອາຈານ, ອາຈານທີ່ປຶກສາ ແລະ ອື່ນໆ) ແລະ ສິດຂອງຜູ້ໃຊ້.
- ທັງສອງໃຊ້ການເຂົ້າສູ່ລະບົບດຽວກັນ (`/accounts/login/`, django-allauth) ແລະ ນະໂຍບາຍການຢືນຢັນສອງຂັ້ນຕອນດຽວກັນ.

## ເທັກໂນໂລຊີ

Python 3.14, Django 6.1, django-unfold (ໜ້າບໍລິຫານ), HTMX 2, Alpine.js 3, Tailwind CSS 4 ແລະ Vite (ພອດທໍ, django-vite), PostgreSQL 18 (ຄວາມປອດໄພລະດັບແຖວ, ການກວດສອບດ້ວຍ trigger), Redis, Celery ແລະ Flower (ຄິວ), Gotenberg (PDF), django-allauth (ການເຂົ້າສູ່ລະບົບ, ການຢືນຢັນສອງຂັ້ນຕອນ, SSO), Django REST framework (API). dependency ຖືກລັອກເວີຊັນດ້ວຍ [uv](https://docs.astral.sh/uv/) (`uv.lock`) ແລະ npm (`package-lock.json`).

## ການກະກຽມສະພາບແວດລ້ອມພັດທະນາ

### ແລ່ນດ້ວຍ uv

ເຄື່ອງຕ້ອງມີ PostgreSQL 18, Redis 8, Gotenberg 8 ແລະ Mailpit (ຫຼື ເປີດສະເພາະບໍລິການເຫຼົ່ານີ້ດ້ວຍ Docker Compose: `docker compose up -d pgsql redis gotenberg mailpit`).

```bash
uv sync                                         # .venv ລວມທັງເຄື່ອງມືພັດທະນາ
npm ci && npm run build                         # static/dist/ (ຫຼື `npm run dev` + VITE_DEV_MODE=true ໃນລະຫວ່າງພັດທະນາ)
cp .env.example .env                            # ໃສ່ DJANGO_SECRET_KEY, ກະແຈ PII (uv run manage.py pii_generate_key) ແລະ ອື່ນໆ
# ບົດບາດ ແລະ ຖານຂໍ້ມູນ (superuser ແລ່ນຄັ້ງດຽວ): docs/manual/lo/operations/installation.md ພາກທີ 2
uv run manage.py migrate                        # migration ຜ່ານການເຊື່ອມຕໍ່ app_migrator
uv run manage.py compilemessages --ignore=.venv
uv run manage.py security_sync_permissions
uv run manage.py security_create_administrator  # ຜູ້ບໍລິຫານຄົນທຳອິດ (createsuperuser ຖືກປິດ)
uv run manage.py runserver
```

- ພອດທໍ: http://localhost:8000/portal/ · ໜ້າບໍລິຫານ: http://localhost:8000/admin/ (ເຂົ້າສູ່ລະບົບດຽວກັນ)
- ກວດອີເມວ (Mailpit): http://localhost:8025

### Docker Compose

ເຄື່ອງ host ຕ້ອງມີພຽງ Docker.

```bash
cp .env.example .env
docker compose up -d                            # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py migrate
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py security_sync_permissions
docker compose exec app uv run manage.py security_create_administrator
docker compose --profile vite up -d vite        # ທາງເລືອກ: Vite dev server (HMR), VITE_DEV_MODE=true ໃນ .env
```

ເມື່ອ container `pgsql` ເລີ່ມເທື່ອທຳອິດ ຈະສ້າງບົດບາດ DB (`app_migrator`, `app_runtime`, `app_reporting`) ແລະ ກະກຽມ DB ພັດທະນາ ແລະ DB ທົດສອບ (`docker/pgsql/`). ຕົວຕິດຕາມຄິວ (Flower): http://localhost:5555

ຂັ້ນຕອນທັງໝົດ ແລະ ການນຳໃຊ້ຈິງ ເບິ່ງ [ຄູ່ມືການຕິດຕັ້ງ](docs/manual/lo/operations/installation.md). ຂໍ້ມູນເດໂມ (`setup_demo`) ແລະ ບັນຊີເດໂມຈະເພີ່ມໃນ Phase 1.

## ຄຳສັ່ງທີ່ໃຊ້ເລື້ອຍ

| ຄຳສັ່ງ | ເນື້ອໃນ |
|---|---|
| `uv run pytest -n auto -m "not concurrency"` | ການທົດສອບ (ການທົດສອບພ້ອມກັນແລ່ນແຍກດ້ວຍ `-m concurrency`) |
| `uv run ruff format && uv run ruff check` | ຮູບແບບໂຄດ ແລະ ການກວດແບບສະຖິດ |
| `uv run mypy ninefruits config` | ການກວດປະເພດ |
| `uv run tools/checks/raw_sql.py` | ການກວດ SQL ດິບ (ຫ້າມສ້າງ SQL ດ້ວຍການຕໍ່ string) |
| `uv run manage.py naming_check` | ການກວດການຕັ້ງຊື່ (ຕາຕະລາງ ແລະ ຖັນ DB, migration, ຄຳສັ່ງ, ການແປ) |
| `uv run manage.py i18n_missing --strict` | ກວດການແປທີ່ຂາດ |
| `uv run manage.py migrate` | migration (ໃຊ້ການເຊື່ອມຕໍ່ `app_migrator` ອັດຕະໂນມັດ) |
| `uv run manage.py security_sync_permissions` | ນຳລາຍການສິດໃນໂຄດເຂົ້າ DB |
| `pre-commit install` | ແລ່ນ ruff, mypy ແລະ ການກວດ SQL ດິບກ່ອນ commit |

ລາຍການທັງໝົດຢູ່ໃນ [ເອກະສານອ້າງອີງຄຳສັ່ງ](docs/manual/lo/operations/commands.md). CI (`.github/workflows/ci.yml`) ແລ່ນການກວດດຽວກັນໃນສອງ job: ຄຸນນະພາບ ແລະ ການທົດສອບ.

## ເອກະສານ

- [ຄູ່ມື](docs/manual/lo/README.md): ຄູ່ມືຜູ້ບໍລິຫານ 28 ບົດ, ຄູ່ມືການດຳເນີນງານ 9 ເອກະສານ
- ການດຳເນີນງານ: [ການຕິດຕັ້ງ](docs/manual/lo/operations/installation.md), [ຄຳສັ່ງ](docs/manual/lo/operations/commands.md), [ກະແຈຄວາມປອດໄພ](docs/manual/lo/operations/security-keys.md)
- ກົດລະບຽບການພັດທະນາ (ພາສາເກົາຫຼີ): [ກົດການຕັ້ງຊື່](docs/development/naming.md), [ລາຍການກວດສອບການ review](docs/development/review-checklist.md)

## ໃບອະນຸຍາດ

[ໃບອະນຸຍາດ MIT](LICENSE). ທຸກຄົນສາມາດໃຊ້, ແກ້ໄຂ ແລະ ແຈກຢາຍໄດ້ຢ່າງເສລີ ໂດຍຮັກສາການແຈ້ງລິຂະສິດ ແລະ ຂໍ້ຄວາມໃບອະນຸຍາດໄວ້ນຳ.

---

**ຄຳຂອບໃຈ**

ຂໍສະແດງຄວາມຂອບໃຈຕໍ່ YUSTIC (ລະບົບເຄືອຂ່າຍບໍລິຫານການສຶກສາຂອງມະຫາວິທະຍາໄລວິທະຍາສາດ ແລະ ເທັກໂນໂລຊີ Yanbian) ທີ່ເຮັດໃຫ້ລະບົບນີ້ເປັນໄປໄດ້. YUSTIC ແມ່ນຜົນງານທີ່ທີມພັດທະນາຈຳນວນບໍ່ຫຼາຍຄົນໄດ້ຮ່ວມກັນຫຼັ່ງເຫື່ອ, ຝັນ ແລະ ທຸ່ມເທສ້າງຂຶ້ນມາຕະຫຼອດຫຼາຍປີ. ການພັດທະນາລະບົບນີ້ແມ່ນການສະແດງຄວາມຄິດຮອດ, ຄວາມເຄົາລົບ ແລະ ຄວາມຂອບໃຈຕໍ່ເພື່ອນຮ່ວມງານທີ່ເຄີຍຮ່ວມເຮັດວຽກນຳກັນ.
