# Pengurusan kunci

- Pembaca: pengendali IT
- Berkaitan: [pemasangan](installation.md), [rujukan arahan](commands.md), [senarai semak pelaksanaan](deployment-checklist.md)

| Kunci | Tujuan | Jika hilang | Penggiliran |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Sesi, CSRF, tandatangan (pautan tetapan semula kata laluan, pautan pengesahan e-mel, kuki peranti yang diingati), hash kod dua faktor e-mel, penyulitan rahsia dua faktor (rahsia TOTP aplikasi pengesah, kod pemulihan) dan rahsia klien SSO | Setiap pengguna dilog keluar, pautan yang telah dihantar berhenti berfungsi, aplikasi pengesah dan kod pemulihan yang telah didaftarkan berhenti berfungsi (tetapan semula dua faktor bagi setiap pengguna diperlukan), rahsia klien SSO mesti dimasukkan semula | Gilirkan dengan kunci sebelumnya dalam `DJANGO_SECRET_KEY_FALLBACKS` (prosedur di bawah) |
| `PII_ENCRYPTION_KEY` | Penyulitan data peribadi seperti nombor kad pengenalan (AES-256-GCM) | **Data peribadi yang disulitkan tidak dapat dipulihkan** | Gilirkan dengan kunci sebelumnya dalam `PII_PREVIOUS_KEYS` (prosedur di bawah) |
| `PII_HASH_KEY` | Hash untuk carian padanan tepat data peribadi (HMAC-SHA256) | Carian berhenti berfungsi (data kekal) | Pada dasarnya tidak digilirkan |

Cipta `DJANGO_SECRET_KEY` dengan `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` dan kedua-dua kunci data peribadi dengan `uv run manage.py pii_generate_key`.

Prinsip penyimpanan

- Simpan sekurang-kurangnya dua salinan ketiga-tiga kunci di luar konfigurasi pelayan, dalam stor rahsia (Vault, pengurus rahsia awan, dsb.) atau dalam storan luar talian yang dimeterai.
- Jangan menyimpannya bersama fail sandaran. Sandaran pangkalan data yang bocor mesti tidak boleh dibaca tanpa kunci.
- Jangan sekali-kali menggunakan kunci daripada `.env` pembangunan atau tetapan ujian dalam pengeluaran.
- Proses web (gunicorn), pekerja Celery dan Celery beat mesti membaca nilai kunci yang sama. Selepas menukar kunci, mulakan semula ketiga-tiganya bersama.

## Menggilirkan `DJANGO_SECRET_KEY`

Gunakan ini untuk penggiliran berjadual atau apabila orang yang mengetahui kunci berubah. Ia bergantung pada `SECRET_KEY_FALLBACKS` Django, jadi tiada sesiapa dilog keluar selagi kunci sebelumnya disimpan. Ini adalah pendekatan yang sama seperti `APP_PREVIOUS_KEYS` dalam sistem asal (Laravel).

1. Cipta kunci baharu: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`.
2. Letakkan kunci semasa di hadapan dalam `DJANGO_SECRET_KEY_FALLBACKS` (dipisahkan dengan koma jika lebih daripada satu) dan kunci baharu dalam `DJANGO_SECRET_KEY`.
   ```
   DJANGO_SECRET_KEY=<new key>
   DJANGO_SECRET_KEY_FALLBACKS=<previous key>
   ```
3. Mulakan semula gunicorn, pekerja Celery dan beat (Docker: `docker compose restart app worker beat`).
4. Sulitkan semula rahsia dua faktor dan rahsia klien SSO dengan kunci baharu. Semak bilangannya dengan `uv run manage.py security_reencrypt_secrets --dry-run`, jalankannya tanpa `--dry-run`, kemudian pastikan `--dry-run` melaporkan 0. Jika kunci sebelumnya dibuang sebelum langkah ini, aplikasi pengesah dan kod pemulihan berhenti berfungsi.
5. Tentukan berapa lama kunci sebelumnya disimpan. Item berikut hanya kekal sah selagi ia disimpan:

   | Item | Selagi kunci sebelumnya disimpan | Selepas ia dibuang |
   |---|---|---|
   | Sesi log masuk | Dipindahkan ke kunci baharu pada permintaan pertamanya selepas penggiliran | Hanya sesi yang tidak digunakan dalam tempoh itu dilog keluar |
   | Pautan tetapan semula kata laluan, pautan pengesahan e-mel | Sah (3 hari) | Mesti dimohon semula |
   | Kuki peranti yang diingati | Sah (tempoh ingatan dalam tetapan keselamatan, 30 hari secara lalai) | Pengesahan dua faktor diminta semula pada log masuk seterusnya |
   | Kod dua faktor e-mel | Kod yang dihantar sejurus sebelum penggiliran tidak sepadan (sah 10 minit) | Sama |

   Simpan sekurang-kurangnya 3 hari, atau sepanjang tempoh ingatan untuk mengekalkan peranti yang diingati.
6. Apabila tempoh tersebut tamat, buang kunci sebelumnya daripada `DJANGO_SECRET_KEY_FALLBACKS` dan mulakan semula seperti dalam langkah 3.
7. Simpan kunci sebelumnya dalam keadaan dimeterai sepanjang tempoh simpanan sandaran. Rahsia dua faktor dalam sandaran yang lebih lama disulitkan dengannya. Apabila memulihkan sandaran yang lebih lama, letakkan kunci tersebut dalam `DJANGO_SECRET_KEY_FALLBACKS` dan jalankan langkah 4.

### Jika kunci bocor

1. Jalankan langkah 1 hingga 4 serta-merta (kunci sebelumnya hanya diperlukan untuk penyulitan semula dalam langkah 4).
2. Sebaik sahaja langkah 4 selesai, buang kunci sebelumnya dan mulakan semula. Setiap sesi tamat dan pautan yang telah dihantar serta peranti yang diingati menjadi tidak sah (hasil yang dikehendaki).
3. Semak log masuk dan kerja pentadbiran sepanjang tempoh pendedahan dalam log keselamatan ([audit dan penyelenggaraan](audit-and-maintenance.md)).

## Menggilirkan kunci data peribadi

1. Cipta kunci baharu dengan `uv run manage.py pii_generate_key` (gunakan hanya `PII_ENCRYPTION_KEY` daripada output).
2. Letakkan kunci semasa dalam `PII_PREVIOUS_KEYS` (dipisahkan dengan koma jika lebih daripada satu) dan kunci baharu dalam `PII_ENCRYPTION_KEY`.
3. Jadikan proses membaca semula konfigurasi: mulakan semula gunicorn dan pekerja Celery (Docker: `docker compose restart app worker beat`).
4. Bagi setiap model yang mempunyai data peribadi, semak bilangan rekod dengan `uv run manage.py pii_reencrypt {app.Model} --dry-run` (contohnya `person.Person`), kemudian jalankannya tanpa `--force` (jawab pengesahan).
5. Setelah Flower menunjukkan tugas selesai dan `--dry-run` melaporkan 0, buang kunci sebelumnya daripada `PII_PREVIOUS_KEYS`.
6. Simpan kunci sebelumnya dalam keadaan dimeterai sepanjang tempoh simpanan sandaran (ia diperlukan untuk memulihkan sandaran yang lebih lama).

Menukar `PII_HASH_KEY` menjadikan setiap hash carian yang disimpan salah, jadi carian padanan tepat mengikut nombor kad pengenalan atau nombor pasport gagal. Pada dasarnya ia tidak digilirkan.
