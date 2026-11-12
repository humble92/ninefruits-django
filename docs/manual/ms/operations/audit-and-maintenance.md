# Integriti audit dan penyelenggaraan berkala

- Pembaca: pengendali IT, pegawai keselamatan
- Berkaitan: [manual pentadbir bab 4, audit](../admin/04-audit.md), [rujukan arahan](commands.md), [sandaran dan pemulihan](backup-restore.md)

## Rantaian hash audit

Jadual audit (`audit.record_changes` untuk perubahan data, `audit.activity_log` untuk aktiviti urusan, `audit.security_events` untuk peristiwa keselamatan) hanya membenarkan penambahan baris (dikuatkuasakan oleh trigger). Selain itu, terdapat mekanisme yang **mendedahkan** sebarang pengubahan tanpa kebenaran.

- Setiap baris menerima SHA-256 bagi kandungannya (`row_hash`) semasa ia dimasukkan.
- `audit_seal` (tugas berjadual `audit.seal`, setiap hari pada 03:30) memautkan baris baharu ke dalam rantaian mengikut susunan ID: `chain_hash = SHA-256(previous chain_hash || row_hash)`. Ia memanggil fungsi pangkalan data `audit.seal()` melalui sambungan pemilik skema (`migrator`).
- `audit_verify_chain` mengira semula hash kandungan dan rantaian bagi setiap baris. Bagi setiap jadual ia mencetak baris yang disemak, baris yang dimeterai, ketidaksepadanan dan id pertama yang tidak sepadan; baris yang kandungannya berubah dilaporkan sebagai "row mismatch", baris yang hilang atau bertukar susunan sebagai "chain mismatch", dan arahan itu memulangkan kod keluar 2.

```bash
uv run manage.py audit_seal
uv run manage.py audit_verify_chain
uv run manage.py audit_verify_chain --table=security_events
```

Perkara yang perlu diingat

- Baris yang diubah sebelum dimeterai (dalam hari yang sama) tidak dapat dikesan oleh rantaian. Oleh sebab itu pemeteraian dijalankan setiap hari dan pengesahan dijalankan sebelum sandaran serta semasa semakan keselamatan.
- Apabila pemangkasan (`audit_prune`) membuang baris yang paling lama, pautan baris pertama yang tinggal tidak disemak (julat yang dipangkas disimpan dalam rekod audit arahan pemangkasan).
- Hanya pentadbir pangkalan data (pemilik skema `app_migrator`) boleh menetapkan `app.audit_maintenance = on`. Peranan aplikasi (`app_runtime`) tidak mempunyai keistimewaan UPDATE atau DELETE pada jadual audit.

## Tempoh simpanan dan pemangkasan

1. Tentukan tempoh simpanan (contohnya perubahan data 3 tahun, aktiviti urusan 5 tahun, peristiwa keselamatan 1 tahun).
2. Buat sandaran sebelum memangkas ([sandaran dan pemulihan](backup-restore.md)) dan pastikan rantaian utuh dengan `audit_verify_chain`.
3. Semak bilangan baris dengan `uv run manage.py audit_prune --before=YYYY-MM-DD --table=record_changes --dry-run`, kemudian jalankannya tanpa `--dry-run` (rekodkan akaun pengendali dengan `--actor=`). Baris yang belum dimeterai tidak sekali-kali dipadam, jadi jalankan `audit_seal` terlebih dahulu.
4. Jalankan `audit_verify_chain` sekali lagi selepas pemangkasan.

Pemangkasan itu sendiri direkodkan: setiap larian menulis ke log aktiviti (log `command`) tarikh potong, pilihan, pelaku dan pengguna OS, serta bagi setiap jadual **bilangan baris yang dipadam, julat ID yang dipadam dan chain_hash di sempadan**; pemadaman sebenar juga direkodkan sebagai peristiwa keselamatan `audit.pruned` (**Audit > Peristiwa keselamatan**). Baris rekod ini turut dipautkan ke dalam rantaian pada pemeteraian seterusnya. Sempadan inilah sebabnya `audit_verify_chain` tidak menyemak pautan baris pertama yang tinggal; dengan membandingkan hash sempadan dengan rekod pemangkasan, anda boleh mengesahkan bahawa julat yang dipadam sepadan dengan pemangkasan yang direkodkan.

## Pembersihan fail

`uv run manage.py media_prune_orphans --dry-run` menyenaraikan baris media yang pemiliknya sudah tiada dan direktori tanpa baris (`PRIVATE_MEDIA_ROOT/<media id>/`); tanpa `--dry-run` ia memadamkannya. Ia meliputi foto individu, dokumen permohonan, PDF sijil dan bukti peperiksaan. Jalankannya setiap bulan atau selepas pemadaman pukal.

## Pemeriksaan kesihatan

| Pemeriksaan | Cara | Apabila gagal |
|---|---|---|
| Status perkhidmatan | `GET /api/v1/health/` (tanpa log masuk, untuk pengimbang beban dan pemantauan) | `unavailable` (503) apabila pangkalan data atau cache tidak menjawab, `degraded` (200) apabila degupan jantung penjadual berusia lebih daripada 5 minit, selain itu `ok`. Apabila log masuk dengan kebenaran `Buka panel pentadbiran`, ia juga memaparkan setiap pemeriksaan (`database`, `cache`, `scheduler`) |
| Pemeriksaan penuh | `uv run manage.py system_health_check [--json]` | 12 pemeriksaan: kunci, peranan pangkalan data, RLS, migrasi, katalog kebenaran, Redis, pekerja Celery, Gotenberg, storan, degupan jantung beat. Kod keluar 2 apabila mana-mana gagal |
| Tetapan pengeluaran | `uv run manage.py check --deploy` | Amaran tentang `DEBUG`, pengalihan HTTPS, HSTS, kuki selamat, kunci rahsia |
| Migrasi | `uv run manage.py migrate --check` | Kod keluar 1 apabila terdapat migrasi yang belum digunakan |
| Katalog kebenaran | `uv run manage.py security_sync_permissions` | Membawa senarai kebenaran dalam kod ke pangkalan data (selamat dijalankan semula) |
| Perkhidmatan PDF | `uv run manage.py pdf_sample` | Sambungan Gotenberg, fon |
| Terjemahan | `uv run manage.py i18n_missing --strict` | Kod keluar 2 apabila terdapat terjemahan yang tiada |
| Rantaian audit | `uv run manage.py audit_verify_chain` | Kod keluar 2 apabila terdapat ketidaksepadanan |
| Baris gilir | Flower, `uv run celery -A config inspect ping` | Pekerja tidak menjawab |

Sambungkan pemantauan kepada status HTTP dan nilai `status` bagi `/api/v1/health/`; jalankan yang lain semasa pelaksanaan dan dalam [pemeriksaan berkala](deployment-checklist.md#pemeriksaan-berkala).
