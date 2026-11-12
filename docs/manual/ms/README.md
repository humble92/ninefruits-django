# Manual sistem maklumat pelajar (Bahasa Melayu)

Untuk kakitangan yang mentadbir sistem setiap hari dan untuk pengendali IT yang memasang, melaksanakan dan menyelenggaranya. Skrin tersedia dalam Bahasa Melayu (menu bahasa).

Bahasa lain: [English](../en/README.md), [한국어](../ko/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md), [Deutsch](../de/README.md), [Filipino](../fil/README.md), [Français](../fr/README.md), [日本語](../ja/README.md), [Монгол](../mn/README.md), [नेपाली](../ne/README.md), [Русский](../ru/README.md), [ไทย](../th/README.md), [Türkçe](../tr/README.md), [Oʻzbek](../uz/README.md), [Tiếng Việt](../vi/README.md). Bahasa Korea ialah sumber asal; edisi lain ialah terjemahan yang menunggu semakan penutur asli.

## Manual pentadbir

[admin/README.md](admin/README.md) — bab 1 hingga 28, daripada permulaan serta pengguna dan peranan hingga persediaan institusi, kemasukan, pendaftaran kursus, gred, sijil, pengijazahan dan integrasi LMS.

## Operasi

| Fail | Kandungan |
|---|---|
| [installation.md](operations/installation.md) | Keperluan, peranan pangkalan data, konfigurasi persekitaran, pemasangan pertama dan kemas kini |
| [deployment-checklist.md](operations/deployment-checklist.md) | Tetapan Python dan gunicorn, pemboleh ubah persekitaran produksi, prosedur pelaksanaan, pemeriksaan berkala |
| [commands.md](operations/commands.md) | Rujukan bagi setiap arahan pengurusan (`uv run manage.py ...`): pilihan, rekod audit, kod keluar, contoh |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | Proses yang berjalan berterusan (pekerja Celery, beat), tugas berjadual dan tugas baris gilir, cara mengesan kegagalan (Flower) |
| [backup-restore.md](operations/backup-restore.md) | Perkara yang perlu disandarkan, contoh dump dan pemulihan, latihan pemulihan |
| [security-keys.md](operations/security-keys.md) | Tiga kunci rahsia, cara menyimpannya, penggiliran kunci data peribadi |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | Rantaian hash audit, tempoh simpanan dan pemangkasan, pembersihan fail, pemeriksaan kesihatan |
| [load-testing.md](operations/load-testing.md) | Ujian beban untuk puncak pendaftaran kursus (Locust) dan keputusan tentang bilangan pekerja |
| [troubleshooting.md](operations/troubleshooting.md) | Gejala biasa, perkara yang perlu disemak, pengesanan bagi setiap permintaan |

## Dokumen lain

- [Panduan integrasi LMS](../../lms-integration-guide.md): API dan penyambung LMS (pembangun)
- [Menambah bahasa](../../development/adding-a-language.md), [peraturan penamaan](../../development/naming.md), [senarai semak semakan kod](../../development/review-checklist.md) (pembangun)
- [Indeks dokumentasi](../../README.md)
