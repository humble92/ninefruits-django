# ວຽກຕາມກຳນົດເວລາ ແລະ ຄິວ

- ກຸ່ມເປົ້າໝາຍ: ຜູ້ປະຕິບັດງານ IT
- ກ່ຽວຂ້ອງ: [ລາຍການກວດສອບການນຳໃຊ້ລະບົບ](deployment-checklist.md), [ຄວາມຖືກຕ້ອງຄົບຖ້ວນຂອງບັນທຶກການກວດສອບ](audit-and-maintenance.md), [ເອກະສານອ້າງອີງຄຳສັ່ງ](commands.md)

## ໂປຣເຊສທີ່ແລ່ນຕະຫຼອດເວລາ

| ໂປຣເຊສ | ຄຳສັ່ງ | ການກວດ |
|---|---|---|
| ເວັບ | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| ຕົວປະມວນຜົນຄິວ (worker) | `uv run celery -A config worker --loglevel=INFO` | **Workers** ໃນ Flower, `uv run celery -A config inspect ping` |
| ຕົວກຳນົດເວລາ (beat) | `uv run celery -A config beat --loglevel=INFO` (**ພຽງໂປຣເຊສດຽວທັງໝົດ**) | `scheduler` ໃນ `/api/v1/health/`, log ຂອງ beat |
| ຕົວຕິດຕາມຄິວ (ທາງເລືອກ) | `uv run celery -A config flower --port=5555` | ວາງໄວ້ໃນເຄືອຂ່າຍພາຍໃນ ຫຼື ຫຼັງການຈຳກັດການເຂົ້າເຖິງຂອງ Nginx ເທົ່ານັ້ນ |

ທັງສາມໂປຣເຊສໃຊ້ໂຄດ ແລະ ຕົວແປສະພາບແວດລ້ອມດຽວກັນ. ຕົວຢ່າງ systemd:

```ini
# /etc/systemd/system/ninefruits-celery.service
[Service]
User=ninefruits
WorkingDirectory=/srv/ninefruits
EnvironmentFile=/etc/ninefruits/env
ExecStart=/usr/local/bin/uv run --no-sync celery -A config worker --loglevel=INFO
KillSignal=SIGTERM
TimeoutStopSec=300
Restart=always
```

ສຳລັບ beat ໃຫ້ສ້າງ service ຮູບແບບດຽວກັນອີກອັນໜຶ່ງດ້ວຍ `ExecStart=... celery -A config beat --loglevel=INFO`. ເຖິງຈະມີຫຼາຍເຊີບເວີ ກໍເປີດ service ຂອງ beat ພຽງເຄື່ອງດຽວ.

## ວຽກຕາມກຳນົດເວລາ

ການລົງທະບຽນແມ່ນ `beat_schedule` ໃນ `config/celery.py` ແລະ beat ຈະປັບ DB scheduler ຂອງ django-celery-beat (ຕາຕະລາງ `django_celery_beat_*`) ໃຫ້ກົງກັນເມື່ອເລີ່ມ. ເວລາອ້າງອີງຕາມເຂດເວລາຂອງເຊີບເວີ (`APP_TIMEZONE`, ຄ່າເລີ່ມຕົ້ນ UTC). ວຽກຕາມກຳນົດເວລາທຸກວຽກຖື Redis lock (`single_instance`) ດັ່ງນັ້ນວຽກດຽວກັນຈະບໍ່ແລ່ນສອງເທື່ອພ້ອມກັນ.

| ວຽກ (ຊື່ Celery) | ຄວາມຖີ່ | ຄຳສັ່ງທີ່ເຮັດວຽກດຽວກັນ | ການກວດຈັບຄວາມລົ້ມເຫຼວ |
|---|---|---|---|
| `admission.expire_drafts` | ທຸກວັນ 03:10 | `admission_expire_drafts` | ແລ່ນຄຳສັ່ງໂດຍກົງ ຈຶ່ງບັນທຶກລົງບັນທຶກການກວດສອບທາງທຸລະກິດ (log `command`) ທຸກຄັ້ງທີ່ແລ່ນ. ຖ້າບໍ່ມີບັນທຶກເກີນໜຶ່ງມື້ ໃຫ້ກວດ beat ແລະ worker |
| `registration.release_reserved_seats` | ທຸກ 5 ນາທີ | `registration_release_reserved_seats` | ບໍ່ມີບັນທຶກການກວດສອບ. ຖ້າ `release_processed_at` ຂອງການຈັດສັນບ່ອນນັ່ງທີ່ເລີຍເວລາປ່ຽນແລ້ວຍັງວ່າງຢູ່ ໃຫ້ກວດ beat |
| `registration.promote_waitlists` | ທຸກຊົ່ວໂມງ (ຕົງຊົ່ວໂມງ) | `waitlist_promote` | ບໍ່ມີບັນທຶກການກວດສອບທາງທຸລະກິດ (ການລົງທະບຽນທີ່ຖືກເລື່ອນຂຶ້ນຈະຢູ່ໃນການປ່ຽນແປງຂໍ້ມູນເປັນ `system:task:registration.promote_waitlists`). ຜົນຂອງວຽກໃນ Flower (ຈຳນວນກຸ່ມຮຽນ, ຈຳນວນທີ່ເລື່ອນຂຶ້ນ) |
| `lms.reconcile` | ທຸກວັນ 02:30 | `lms_reconcile` | ບັນທຶກການຊິງຕໍ່ການເຊື່ອມຕໍ່ (ໜ້າບໍລິຫານ **ການເຊື່ອມຕໍ່ LMS**), ຜົນຂອງວຽກໃນ Flower |
| `audit.seal` | ທຸກວັນ 03:30 | `audit_seal` | ປະທັບຕາຕ່ອງໂສ້ແຮດຊ໌ຂອງບັນທຶກການກວດສອບ ([ຄວາມຖືກຕ້ອງຄົບຖ້ວນຂອງບັນທຶກການກວດສອບ](audit-and-maintenance.md)). ກວດຖ້າ `audit_verify_chain` ສະແດງແຖວທີ່ຍັງບໍ່ປະທັບຕາຫຼາຍກວ່າປະລິມານຂອງມື້ດຽວ |
| `core.heartbeat` | ທຸກນາທີ | ບໍ່ມີ | ບັນທຶກເວລາແລ່ນຄັ້ງສຸດທ້າຍລົງ cache key `system:heartbeat`. ຖ້າບໍ່ມີການອັບເດດເກີນ 5 ນາທີ `/api/v1/health/` ຈະຕອບ `degraded` |

## ວຽກໃນຄິວ

| ວຽກ (ຊື່ Celery) | ເກີດຂຶ້ນເມື່ອ | ໝາຍເຫດ |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | ໜຶ່ງວຽກຕໍ່ຊຸດຂອງແຖວ (group). ຖ້າມີຊຸດທີ່ລົ້ມເຫຼວ ໃຫ້ແລ່ນຄຳສັ່ງຄືນ (ແຖວທີ່ໃຊ້ກະແຈປັດຈຸບັນແລ້ວຈະຖືກຂ້າມ) |
| `registration.promote_waitlist` | ການຍົກເລີກ/ຖອນການລົງທະບຽນຮຽນ, ການປ່ຽນການຈັດສັນບ່ອນນັ່ງ | ແລ່ນພຽງໜຶ່ງວຽກຕໍ່ກຸ່ມຮຽນ (Redis lock, ປ້ອງກັນການຊ້ຳກັນ). ການເລື່ອນຂຶ້ນຈາກລາຍຊື່ລໍຖ້າຈະກວດທຸກກົດລະບຽບການລົງທະບຽນຮຽນຄືນໃໝ່. ເຂົ້າຄິວຫຼັງ transaction commit ແລ້ວ |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, ການປິດພາກຮຽນໃນໜ້າບໍລິຫານ | chord: ວຽກຊຸດລະ 100 ນັກສຶກສາ ແລ້ວຕາມດ້ວຍວຽກສິ້ນສຸດ (ຈັດອັນດັບນັກສຶກສາດີເດັ່ນ, ປ່ຽນສະຖານະພາກຮຽນ, ແຈ້ງພະນັກງານທີ່ເລີ່ມ). ຄວາມຄືບໜ້າແມ່ນແຖວ `term-close:{ລະຫັດພາກຮຽນ}` ຂອງ `job_batches` ເຊິ່ງສະແດງໃນໜ້າບໍລິຫານ. ວຽກແຕ່ລະຊຸດລອງໃໝ່ສູງສຸດ 3 ຄັ້ງເມື່ອເກີດຂໍ້ຜິດພາດ DB; ຖ້າຍັງລົ້ມເຫຼວ ທັງຊຸດຈະຖືກໝາຍວ່າລົ້ມເຫຼວ ແລະ ວຽກສິ້ນສຸດຈະບໍ່ແລ່ນ. ແກ້ສາເຫດແລ້ວເລີ່ມການປິດພາກຮຽນໃໝ່ (ການຄຳນວນຕໍ່ນັກສຶກສາແລ່ນຊ້ຳໄດ້ຜົນດຽວກັນ) |
| `importing.import_chunk` | ການນຳເຂົ້າ CSV ໃນໜ້າບໍລິຫານ, `reference_import` | ໜຶ່ງວຽກຕໍ່ຊິ້ນ. ຜົນຢູ່ໃນ `imports`, ແຖວທີ່ລົ້ມເຫຼວຢູ່ໃນ `failed_import_rows` (ຜົນການນຳເຂົ້າໃນໜ້າບໍລິຫານ) |
| `lms.sync_section`, `lms.sync_enrollment` | ເຫດການປ່ຽນແປງກຸ່ມຮຽນ ແລະ ການລົງທະບຽນຮຽນ | ເມື່ອລົ້ມເຫຼວຈະລອງໃໝ່ສູງສຸດ 3 ຄັ້ງ ຫ່າງກັນ 1 ນາທີ. ສ່ວນທີ່ຍັງຕ່າງກັນ `lms.reconcile` ຕອນກາງຄືນຈະແກ້ໃຫ້ |

ໃນຂະນະທີ່ວຽກແລ່ນ ຜູ້ປະຕິບັດຂອງ DB ຈະຖືກບັນທຶກເປັນ `system:task:{ຊື່ວຽກ}` (ຕົວຢ່າງ `system:task:grading.close_term_records`) ພ້ອມກັບ ID ຄຳຮ້ອງຂໍ ແລະ ຜູ້ໃຊ້ຂອງຄຳຮ້ອງຂໍທີ່ເຮັດໃຫ້ເກີດວຽກນັ້ນ.

ເບິ່ງວຽກທີ່ລົ້ມເຫຼວ (**Tasks**, ສະຖານະ `FAILURE`) ແລະ exception ໃນ Flower. ວຽກ Celery ໃຊ້ `acks_late` ດັ່ງນັ້ນຖ້າ worker ຕາຍລະຫວ່າງແລ່ນ ວຽກຈະຖືກແລ່ນຄືນ. ທຸກວຽກຖືກອອກແບບໃຫ້ແລ່ນຊ້ຳໄດ້ຜົນດຽວກັນ (idempotent).
