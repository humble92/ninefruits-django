# ການສຳຮອງ ແລະ ກູ້ຄືນຂໍ້ມູນ

- ກຸ່ມເປົ້າໝາຍ: ຜູ້ປະຕິບັດງານ IT
- ກ່ຽວຂ້ອງ: [ການຕິດຕັ້ງ](installation.md), [ການຄຸ້ມຄອງກະແຈ](security-keys.md), [ຄວາມຖືກຕ້ອງຄົບຖ້ວນຂອງບັນທຶກການກວດສອບ](audit-and-maintenance.md)

## ສິ່ງທີ່ຕ້ອງສຳຮອງ

| ເປົ້າໝາຍ | ວິທີ | ຄວາມຖີ່ (ແນະນຳ) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` ຫຼື PITR (ເກັບ WAL) | ເຕັມທຸກວັນ + WAL ຕໍ່ເນື່ອງ |
| ບ່ອນເກັບໄຟລ໌ສ່ວນຕົວ (`PRIVATE_MEDIA_ROOT`, ຄ່າເລີ່ມຕົ້ນ `storage/private`) | snapshot ຫຼື bucket ທີ່ມີການຄຸ້ມຄອງເວີຊັນ | ຄວາມຖີ່ດຽວກັນກັບ DB |
| ການຕັ້ງຄ່າສະພາບແວດລ້ອມ ແລະ ກະແຈ (`DJANGO_SECRET_KEY`, `PII_*`, ລະຫັດຜ່ານ DB) | ບ່ອນເກັບຄວາມລັບ (secret store) | ເມື່ອມີການປ່ຽນແປງ |

DB ແລະ ບ່ອນເກັບໄຟລ໌ຕ້ອງສາມາດກູ້ຄືນໄດ້ຢູ່ຈຸດເວລາດຽວກັນ (ຂໍ້ມູນ metadata ຂອງຮູບຖ່າຍ, ເອກະສານສະໝັກ, PDF ໃບຢັ້ງຢືນ ແລະ ຫຼັກຖານການສອບເສັງຢູ່ໃນຕາຕະລາງ `media` ຂອງ DB). ບໍ່ຕ້ອງສຳຮອງ Redis: ມັນມີພຽງ cache, lock ແລະ ຄິວ ແລະ ເຊສຊັນກໍຖືກເກັບໄວ້ໃນ DB ນຳ (`django_session`). ລາຍການວຽກຕາມກຳນົດເວລາ (django-celery-beat) ກໍຢູ່ໃນ DB ແລະ beat ຈະປັບໃຫ້ກົງກັບ `config/celery.py` ຄືນເມື່ອເລີ່ມ.

`staticfiles/` ແລະ `static/dist/` ແມ່ນຜົນຂອງການ build ຈຶ່ງບໍ່ສຳຮອງ (ສ້າງຄືນດ້ວຍ `npm run build` ແລະ `collectstatic`).

## ຕົວຢ່າງການສຳຮອງ DB

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` ເປັນເຈົ້າຂອງທຸກ schema (`public`, `audit`, `reporting`, `util`) ດັ່ງນັ້ນຈຶ່ງສຳຮອງຂໍ້ມູນດ້ວຍບັນຊີນີ້. ບົດບາດ (`app_*`) ເປັນວັດຖຸລະດັບ cluster ຈຶ່ງບໍ່ຢູ່ໃນໄຟລ໌ dump. ໃນເຊີບເວີທີ່ຈະກູ້ຄືນ ໃຫ້ສ້າງບົດບາດຕາມພາກທີ 2 ຂອງ [ການຕິດຕັ້ງ](installation.md) ກ່ອນ.

ຖ້າແລ່ນ `uv run manage.py audit_verify_chain` ກ່ອນສຳຮອງ ກໍສາມາດປຽບທຽບຕ່ອງໂສ້ບັນທຶກການກວດສອບຂອງ DB ທີ່ກູ້ຄືນດ້ວຍຄຳສັ່ງດຽວກັນໄດ້.

## ຕົວຢ່າງການກູ້ຄືນ

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

ເມື່ອແລ່ນແອັບພລິເຄຊັນດ້ວຍ DB ທີ່ກູ້ຄືນ ໃຫ້ໃສ່ `DB_DATABASE=ninefruits_restore` ແລະ **ກະແຈໃນເວລາທີ່ສຳຮອງ** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY` ແລະ `PII_PREVIOUS_KEYS` ຖ້າມີການປ່ຽນກະແຈໃນລະຫວ່າງນັ້ນ). ຈາກນັ້ນກວດສະຖານະ:

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # ເວີຊັນໂຄດ ແລະ schema ກົງກັນບໍ
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

ຖ້າ `migrate --check` ລາຍງານວ່າມີ migration ທີ່ຕ້ອງນຳໃຊ້ ໝາຍຄວາມວ່າການສຳຮອງເກົ່າກວ່າໂຄດປັດຈຸບັນ. ໃຫ້ກູ້ຄືນດ້ວຍໂຄດເວີຊັນດຽວກັນ ຫຼື ອັບເກຣດດ້ວຍ `setup_install --force`.

## ການຝຶກຊ້ອມກູ້ຄືນ

ທຸກໄຕມາດ ໃຫ້ກູ້ຄືນໃສ່ເຊີບເວີແຍກຕ່າງຫາກ ແລະ ກວດສິ່ງຕໍ່ໄປນີ້: ການເຂົ້າສູ່ລະບົບ, ການຖອດລະຫັດຂໍ້ມູນສ່ວນບຸກຄົນ (**ສະແດງເລກບັດປະຈຳຕົວ** ໃນລາຍລະອຽດບຸກຄົນຂອງໜ້າບໍລິຫານ, ກະແຈກົງກັນ), ການເບິ່ງບັນທຶກການກວດສອບ ແລະ `audit_verify_chain`, ການເປີດໄຟລ໌ (ຮູບຖ່າຍ, PDF ໃບຢັ້ງຢືນ), ໜ້າກວດຄວາມແທ້ຂອງໃບຢັ້ງຢືນ. ບັນທຶກຜົນການຝຶກຊ້ອມ (ເວລາທີ່ໃຊ້, ບັນຫາ).
