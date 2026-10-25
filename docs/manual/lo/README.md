# ຄູ່ມື Ninefruits (ພາສາລາວ)

ຄູ່ມືນີ້ສຳລັບພະນັກງານບໍລິຫານການສຶກສາທີ່ໃຊ້ໜ້າບໍລິຫານ ແລະ ຜູ້ປະຕິບັດງານ IT ທີ່ຕິດຕັ້ງ ແລະ ດູແລລະບົບ.

ພາສາອື່ນ: [한국어](../ko/README.md), [English](../en/README.md), [简体中文](../zh_Hans/README.md). ສະບັບພາສາເກົາຫຼີແມ່ນຕົ້ນສະບັບ; ສະບັບອື່ນແມ່ນການແປທີ່ຍັງລໍຖ້າການກວດສອບຈາກເຈົ້າຂອງພາສາ.

## ຄູ່ມືຜູ້ບໍລິຫານ

[ຄູ່ມືຜູ້ບໍລິຫານ](admin/README.md): ບົດທີ 1 ຫາ 28 ແຕ່ລຳດັບການຕັ້ງຄ່າເບື້ອງຕົ້ນຈົນເຖິງວິທີໃຊ້ແຕ່ລະຂົງເຂດ (ຜູ້ໃຊ້ ແລະ ບົດບາດ, ບັນທຶກນັກສຶກສາ, ການຮັບເຂົ້າຮຽນ, ວິຊາ ແລະ ກຸ່ມຮຽນ, ການລົງທະບຽນຮຽນ, ເກຣດ, ໃບຢັ້ງຢືນ, ການສອບເສັງ, ການເຂົ້າຮຽນ, ການຈົບການສຶກສາ, ບົດລາຍງານ, ການເຊື່ອມຕໍ່ LMS).

## ຄູ່ມືການດຳເນີນງານ

| ເອກະສານ | ເນື້ອໃນ |
|---|---|
| [installation.md](operations/installation.md) | ຄວາມຕ້ອງການ, ການກຽມຖານຂໍ້ມູນ ແລະ ບົດບາດ, ການຕັ້ງຄ່າສະພາບແວດລ້ອມ, ການຕິດຕັ້ງ ແລະ ອັບເດດ |
| [commands.md](operations/commands.md) | ເອກະສານອ້າງອີງຄຳສັ່ງບໍລິຫານທັງໝົດ (`uv run manage.py ...`): ການນຳໃຊ້, ຕົວເລືອກ, ການບັນທຶກການກວດສອບ, ລະຫັດອອກ |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | ໂປຣເຊສທີ່ແລ່ນຕະຫຼອດເວລາ (Celery worker, beat), ວຽກຕາມກຳນົດເວລາ ແລະ ວຽກໃນຄິວ (Flower) |
| [backup-restore.md](operations/backup-restore.md) | ສິ່ງທີ່ຕ້ອງສຳຮອງ, ຕົວຢ່າງ pg_dump ແລະ pg_restore, ການຝຶກຊ້ອມກູ້ຄືນ |
| [security-keys.md](operations/security-keys.md) | ກະແຈລັບ 3 ຊະນິດ, ຫຼັກການເກັບຮັກສາ ແລະ ຂັ້ນຕອນການປ່ຽນກະແຈ PII |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | ຕ່ອງໂສ້ແຮດຊ໌ຂອງບັນທຶກການກວດສອບ, ການເກັບຮັກສາ ແລະ ລ້າງຂໍ້ມູນ, ການກວດສຸຂະພາບລະບົບ |
| [deployment-checklist.md](operations/deployment-checklist.md) | ການຕັ້ງຄ່າ Python ແລະ gunicorn, ຕົວແປສະພາບແວດລ້ອມສຳລັບການນຳໃຊ້ຈິງ, ຂັ້ນຕອນການນຳໃຊ້ລະບົບ, ການກວດກາຕາມກຳນົດ |
| [load-testing.md](operations/load-testing.md) | ການທົດສອບພາລະຊ່ວງສູງສຸດຂອງການລົງທະບຽນຮຽນດ້ວຍ Locust ແລະ ເກນທີ່ໃຊ້ຕັດສິນຈຳນວນ worker |
| [troubleshooting.md](operations/troubleshooting.md) | ອາການທີ່ພົບເລື້ອຍ ແລະ ສິ່ງທີ່ຕ້ອງກວດ, ການຕິດຕາມດ້ວຍ X-Request-Id |

## ເອກະສານອື່ນ

- [ຄູ່ມືການເຊື່ອມຕໍ່ LMS](../../lms-integration-guide.md): API ແລະ ຕົວເຊື່ອມຕໍ່ LMS (ນັກພັດທະນາ)
- [ການເພີ່ມພາສາ](../../development/adding-a-language.md), [ກົດການຕັ້ງຊື່](../../development/naming.md), [ລາຍການກວດທົບທວນໂຄດ](../../development/review-checklist.md) (ນັກພັດທະນາ)
- [ສາລະບານເອກະສານ](../../README.md)
