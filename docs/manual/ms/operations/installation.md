# Pemasangan

- Pembaca: pengendali IT
- Berkaitan: [Rujukan arahan](commands.md), [Pengurusan kunci](security-keys.md), [Senarai semak pelaksanaan](deployment-checklist.md)

## 1. Keperluan

| Komponen | Versi | Catatan |
|---|---|---|
| Python | 3.14 | Dipasang dan dijalankan dengan [uv](https://docs.astral.sh/uv/) (`uv sync`). Pakej sistem: `gettext` (mengkompil terjemahan), `libmagic` (pengesanan jenis fail) |
| Node.js | 22 | Membina aset skrin (`npm ci && npm run build`). Pelayan produksi hanya memerlukan output binaan |
| PostgreSQL | 18 | Sambungan `btree_gist` dan `pg_trgm` (dipasang oleh migrasi), kolasi ICU |
| Redis | 8 | Cache, sesi, broker dan hasil Celery |
| Gotenberg | 8 | Penjanaan PDF. Didedahkan hanya pada rangkaian dalaman |
| Pelayan e-mel | SMTP | Penetapan semula kata laluan, kod e-mel pengesahan dua faktor, jemputan, pemberitahuan |
| Pelayan web | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`. Nginx menyajikan `staticfiles/` sendiri dan menghantar yang lain kepada gunicorn |
| Pekerja baris gilir | Pekerja Celery | Pastikan `uv run celery -A config worker` sentiasa berjalan di bawah pengurus proses (systemd, supervisor) |
| Penjadual | Celery beat | Jalankan `uv run celery -A config beat` pada **tepat satu** mesin (penjadual pangkalan data, django-celery-beat) |
| Pemantau baris gilir | Flower (pilihan) | `uv run celery -A config flower`. Simpan pada rangkaian dalaman atau di sebalik sekatan akses Nginx (atau `--basic-auth` Flower); jangan sekali-kali mendedahkannya |

## 2. Penyediaan pangkalan data

Jalankan sekali sebagai superuser pangkalan data. Aplikasi tidak sekali-kali menggunakan superuser.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| Peranan | Pemboleh ubah persekitaran | Tujuan |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | Menjalankan aplikasi (keselamatan peringkat baris terpakai, tiada DDL) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | Migrasi, pemeteraian dan pemangkasan audit sahaja (`migrate` menggunakan sambungan ini secara automatik) |
| `app_reporting` | (dikonfigurasi dalam alat BI) | Membaca skema `reporting` |

Dalam persekitaran pembangunan Docker Compose, `docker/pgsql/20-create-app-roles.sh` melakukan perkara yang sama apabila kontena `pgsql` dimulakan buat kali pertama (peranan, pangkalan data `ninefruits` dan pangkalan data ujian).

## 3. Konfigurasi persekitaran

Salin `.env.example` kepada `.env` dan isikan nilainya (dalam produksi, bekalkannya sebagai pemboleh ubah persekitaran atau daripada stor rahsia). Nilai yang mesti diubah:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. Simpan seperti yang diterangkan dalam [Pengurusan kunci](security-keys.md).
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **Jika kunci ini hilang, data peribadi yang disulitkan tidak dapat dipulihkan.** Simpan secara berasingan seperti yang diterangkan dalam [Pengurusan kunci](security-keys.md).
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: bilangan proksi songsang di hadapan aplikasi (`1` bagi satu Nginx). Lihat [Senarai semak pelaksanaan](deployment-checklist.md#proksi-dan-alamat-klien)
- `INSTITUTION_TIMEZONE`: zon waktu lalai institusi pada pemasangan pertama (contohnya `Asia/Seoul`)

Senarai penuh pemboleh ubah persekitaran produksi terdapat dalam [Senarai semak pelaksanaan](deployment-checklist.md#pemboleh-ubah-persekitaran).

## 4. Pemasangan

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` menjalankan secara berturutan: migrasi (melalui sambungan `app_migrator`), data penting (templat peranan dan penyegerakan kebenaran, negara, bahasa, jenis senarai kod, jenis unit organisasi, jenis perubahan status, himpunan peraturan pendaftaran kursus), nilai lalai institusi (bahasa lalai, zon waktu, nama institusi), penetapan skala gred, profil pemasangan dan pentadbir awal. Dalam skrip pelaksanaan, jalankannya dengan `--force` dan pilihan; kata laluan pentadbir dibaca daripada input standard.

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

Profil pemasangan (`--profile=`, boleh diberikan lebih daripada sekali)

| Kunci | Kandungan |
|---|---|
| `korean-university` | Jenis semester musim bunga/musim panas/musim luruh/musim sejuk, skala gred 4.5, kategori kursus, slot masa bermula pada 09:00, jenis bilik, jenis kemasukan dan dokumen permohonan, borang penilaian kursus lalai, jenis sijil dengan templat dalam empat bahasa |
| `yust-legacy` | Semua dalam `korean-university`, ditambah had kredit mengikut tahun kemasukan dan bagi kejururawatan, kursus bank kredit di luar had, skala gred 4.3 dan dasar penggredannya |

Tanpa profil, masukkan semua ini dalam panel pentadbiran. Menggunakan profil sekali lagi kemudian akan mengekalkan nilai yang telah diubah oleh pentadbir. Skala gred tidak boleh diubah setelah ditetapkan (gred dan PNG disimpan pada skala tersebut).

`createsuperuser` Django dinyahdayakan. Pentadbir awal hanya dicipta dengan `setup_install` atau `security_create_administrator` ([Rujukan arahan](commands.md)).

Selepas pemasangan, pentadbir urusan memasukkan data rujukan mengikut [Manual pentadbir bab 5, susunan persediaan awal](../admin/05-institution-setup.md). Daftarkan proses pelayan (gunicorn, pekerja Celery, beat) seperti yang diterangkan dalam [Senarai semak pelaksanaan](deployment-checklist.md) dan [Tugas berjadual](scheduled-jobs.md).

### Docker Compose (pembangunan)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| Perkhidmatan | Alamat |
|---|---|
| Aplikasi | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (peti mel pembangunan) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Pelayan pembangunan Vite (pilihan, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

Imej produksi ialah sasaran `production` dalam `Dockerfile` (lalai). Ia menjalankan `compilemessages` dan `collectstatic` semasa binaan dan memulakan gunicorn. Imej yang sama menjalankan pekerja dan beat (`uv run --no-sync celery -A config worker|beat`).

## 5. Mengesahkan pemasangan

1. Log masuk sebagai pentadbir awal di `/accounts/login/`. `/admin/` dibuka dan bar sisi memaparkan **Pengguna dan akses**, **Audit** dan **Tetapan**.
2. Tetapkan dasar pengesahan dua faktor di bawah **Tetapan > Keselamatan** dalam panel pentadbiran.
3. Daftarkan pengesahan dua faktor bagi pentadbir (portal **Keselamatan**, `/portal/security/`).
4. Semak perkhidmatan PDF dengan `uv run manage.py pdf_sample`.
5. Pastikan di bawah **Audit > Perubahan data** dalam panel pentadbiran bahawa pemasangan direkodkan sebagai `system:command:setup_install`.
6. Pastikan `uv run manage.py check --deploy` tidak melaporkan amaran produksi dan `GET /api/v1/health/` menjawab `{"status": "ok"}` (beat mesti sudah berjalan selama seminit).

## 6. Mengemas kini

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

Laraskan nama perkhidmatan mengikut pemasangan anda. Ikuti [Senarai semak pelaksanaan](deployment-checklist.md#prosedur-pelaksanaan) untuk sandaran dan semakan sebelum dan selepas kemas kini.
