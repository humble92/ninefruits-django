# Sandaran dan pemulihan

- Pembaca: pengendali IT
- Berkaitan: [pemasangan](installation.md), [pengurusan kunci](security-keys.md), [integriti audit](audit-and-maintenance.md)

## Perkara yang perlu disandarkan

| Sasaran | Kaedah | Kekerapan (disyorkan) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` atau PITR (pengarkiban WAL) | Penuh setiap hari + WAL berterusan |
| Storan fail persendirian (`PRIVATE_MEDIA_ROOT`, lalai `storage/private`) | Snapshot atau bucket berversi | Sama seperti pangkalan data |
| Konfigurasi persekitaran dan kunci (`DJANGO_SECRET_KEY`, `PII_*`, kata laluan pangkalan data) | Stor rahsia | Pada setiap perubahan |

Pangkalan data dan storan fail mesti boleh dipulihkan ke titik masa yang sama (metadata bagi foto, dokumen permohonan, PDF sijil dan bukti peperiksaan disimpan dalam jadual pangkalan data `media`). Redis tidak disandarkan: ia hanya menyimpan cache, kunci dan baris gilir, dan sesi juga disimpan dalam pangkalan data (`django_session`). Senarai tugas berjadual (django-celery-beat) juga berada dalam pangkalan data, dan beat menyelaraskannya semula dengan `config/celery.py` apabila ia bermula.

`staticfiles/` dan `static/dist/` ialah output binaan dan tidak disandarkan (`npm run build` dan `collectstatic` menciptanya semula).

## Contoh sandaran pangkalan data

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` memiliki setiap skema (`public`, `audit`, `reporting`, `util`), jadi buat sandaran dengan akaun ini. Peranan (`app_*`) ialah objek kluster dan tidak termasuk dalam dump. Pada pelayan pemulihan, cipta peranan terlebih dahulu seperti yang diterangkan dalam [Pemasangan](installation.md) bahagian 2.

Jika anda menjalankan `uv run manage.py audit_verify_chain` sebelum sandaran, arahan yang sama pada pangkalan data yang dipulihkan membolehkan anda membandingkan rantaian audit.

## Contoh pemulihan

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

Untuk menjalankan aplikasi pada pangkalan data yang dipulihkan, tetapkan `DB_DATABASE=ninefruits_restore` dan **kunci daripada masa sandaran** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, dan `PII_PREVIOUS_KEYS` jika kunci telah digilirkan sejak itu). Kemudian semak keadaannya:

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

Jika `migrate --check` melaporkan migrasi yang perlu digunakan, sandaran tersebut lebih lama daripada kod semasa. Pulihkan dengan kod versi yang sama, atau naik taraf dengan `setup_install --force`.

## Latihan pemulihan

Setiap suku tahun, pulihkan ke pelayan berasingan dan sahkan perkara berikut: log masuk, penyahsulitan data peribadi (**Papar nombor kad pengenalan** pada seseorang individu dalam panel pentadbiran; kunci sepadan), paparan rekod audit dan `audit_verify_chain`, pembukaan fail (foto, PDF sijil), halaman pengesahan sijil. Rekodkan hasilnya (masa yang diambil, masalah).
