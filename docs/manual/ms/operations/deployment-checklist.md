# Senarai semak pelaksanaan dan tetapan gunicorn serta Python

- Pembaca: pengendali IT
- Berkaitan: [Pemasangan](installation.md), [Pengurusan kunci](security-keys.md), [Tugas berjadual](scheduled-jobs.md), [Ujian beban](load-testing.md)

## Python dan kebergantungan

- Gunakan keluaran tampalan terkini bagi **Python 3.14**. Semasa membina imej kontena atau pelayan, jangan kunci versi tampalan Python; ambil yang terkini (`python:3.14-slim` dalam `Dockerfile`).
- Kebergantungan Python dikunci dalam `uv.lock`. Pemasangan produksi sentiasa menggunakan `uv sync --frozen --no-dev` (ia gagal jika fail kunci tidak sepadan). Alat pembangunan (pytest, ruff, mypy, Playwright) tidak sekali-kali sampai ke produksi.
- Apabila Django menerbitkan keluaran keselamatan, naik taraf dengan `uv lock --upgrade-package django`, jalankan ujian dan laksanakan. Semak kerentanan kebergantungan seperti yang dilakukan oleh CI: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`.
- `uv run manage.py check --deploy` memberi amaran tentang tetapan produksi (`DEBUG`, HTTPS, kuki, HSTS, panjang kunci rahsia). Setiap pelaksanaan mesti mempunyai sifar amaran.

## gunicorn dan Nginx

| Perkara | Nilai | Sebab |
|---|---|---|
| Menjalankan gunicorn | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, pekerja segerak. Bilangan pekerja dan saiz kolam sambungan diambil daripada pemboleh ubah persekitaran; alasannya terdapat dalam [Ujian beban](load-testing.md) |
| Ikatan gunicorn | `127.0.0.1:8000` atau soket Unix | Jangan sekali-kali mendedahkan gunicorn secara terus; sentiasa letakkannya di sebalik Nginx |
| Mula semula pekerja | `HUP` semasa pelaksanaan (`reload` systemd) | Menyelesaikan permintaan yang sedang berjalan dan menggantikan pekerja dengan kod baharu |
| Sambungan pangkalan data | Dengan `DB_POOL=true`, satu kolam sambungan psycopg bagi setiap pekerja (`DB_POOL_MIN`, `DB_POOL_MAX`) | Pekerja × `DB_POOL_MAX` + sambungan Celery mesti kekal di bawah `max_connections` PostgreSQL. Sambungan yang dikembalikan ke kolam dikosongkan pelaku sesi pangkalan datanya (`ninefruits.core.pool.reset_connection`) |
| `client_max_body_size` Nginx | `32m` | Had atas bagi muat naik dokumen kemasukan, bukti peperiksaan dan foto (dengan ruang lebihan di atas pengesahan aplikasi 5MB dan 2MB) |
| Fail statik Nginx | `location /static/ { alias <repository>/staticfiles/; }` | Nginx menyajikan output `collectstatic` sendiri |
| Fail peribadi | **Jangan sekali-kali memetakan** `PRIVATE_MEDIA_ROOT` (lalai `storage/private`) dalam Nginx | Foto, dokumen permohonan dan PDF sijil dimuat turun hanya melalui paparan yang menyemak kebenaran |
| Pengepala Nginx | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, secara pilihan `X-Request-Id $request_id` | Alamat klien, pengesanan HTTPS, pengesanan bagi setiap permintaan |
| Gotenberg, Redis, PostgreSQL | Alamat dalaman sahaja | Tidak sekali-kali didedahkan ke luar |

```nginx
server {
    listen 443 ssl;
    server_name sis.example.ac.kr;
    client_max_body_size 32m;

    location /static/ { alias /srv/ninefruits/staticfiles/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-Id $request_id;
    }
}
```

### Proksi dan alamat klien

Had log masuk, had kadar API dan alamat IP dalam rekod audit menggunakan alamat klien yang ditentukan oleh `ninefruits.core.http.client_ip`.

- `TRUSTED_PROXY_COUNT`: bilangan proksi songsang di hadapan aplikasi yang menambah entri pada `X-Forwarded-For`. `1` bagi satu Nginx, `2` bagi pengimbang beban ditambah Nginx. `0` (lalai) menggunakan `REMOTE_ADDR`. Entri pada kedudukan sebanyak itu dari kanan ialah alamat klien; entri lebih ke kiri (dihantar oleh klien) tidak sekali-kali dipercayai.
- **Jika nilainya lebih rendah daripada bilangan proksi sebenar**, setiap pengguna kelihatan datang dari alamat Nginx dan had log masuk terpakai kepada seluruh kampus serentak. **Jika lebih tinggi**, aplikasi mempercayai `X-Forwarded-For` yang dihantar oleh klien, dan had tersebut boleh dipintas. Selepas pelaksanaan, pastikan alamat IP di bawah **Audit > Peristiwa keselamatan** dalam panel pentadbiran ialah alamat pengguna sebenar.
- `LOGIN_RATE_LIMIT_PER_IP`: percubaan log masuk bagi setiap alamat klien (django-allauth, lalai `30/m/ip`). Sistem asal tidak mempunyai had sedemikian. Jika seluruh kampus keluar melalui satu alamat NAT, nilai ini terlalu rendah untuk pagi pertama pendaftaran kursus; naikkannya (contohnya `300/m/ip`). Nilai kosong bermaksud tiada had bagi setiap alamat (seperti dalam sistem asal). Had kegagalan bagi setiap akaun (5 seminit) dan penguncian akaun terpakai tanpa mengira nilai ini.

## Pemboleh ubah persekitaran

`.env.example` mengandungi nilai lalai pembangunan. Dalam produksi, suntik rahsia daripada stor rahsia.

| Pemboleh ubah | Nilai produksi | Catatan |
|---|---|---|
| `DJANGO_ENV` | `production` | Menolak `setup_demo` dan membuang lencana persekitaran daripada panel pentadbiran |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, kuki selamat |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | Stor rahsia | [Pengurusan kunci](security-keys.md). Semasa penggiliran, kunci sebelumnya dimasukkan ke dalam `DJANGO_SECRET_KEY_FALLBACKS` |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | Senarai dipisahkan dengan koma |
| `APP_URL` | `https://sis.example.ac.kr` | Pautan dalam e-mel, kod QR pengesahan sijil |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | Stor rahsia | Jika hilang, data peribadi tidak dapat dinyahsulit |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | Aplikasi dan Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | Digunakan oleh `migrate`, `setup_install`, `audit_seal` dan `audit_prune`. Simpan kata laluan hanya pada pelayan yang menjalankan pelaksanaan dan pelayan yang menjalankan pemeteraian audit (`audit_seal`) |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, nilai daripada [Ujian beban](load-testing.md), `60`, `2000`, `127.0.0.1` | Dibaca oleh `config/gunicorn.py`. Bilangan pekerja lalai ialah 2 bagi setiap teras CPU + 1. `GUNICORN_FORWARDED_ALLOW_IPS` hanya menentukan `X-Forwarded-Proto` siapa yang dipercayai oleh gunicorn; alamat klien diambil daripada `TRUSTED_PROXY_COUNT` |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | Nilai yang diputuskan dalam [Ujian beban](load-testing.md): `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` menghidupkan pernyataan tersedia (prepared statement) (mengurangkan kos perancangan pertanyaan RLS); 0 mematikannya |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis dalaman | Broker dan hasil menggunakan `REDIS_URL` secara lalai |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | Geganti SMTP universiti | Jemputan, kod pengesahan dua faktor, pemberitahuan pendaftaran kursus dan gred |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | Alamat dalaman, `60` | |
| `PRIVATE_MEDIA_ROOT` | Cakera yang disandarkan | Storan fail peribadi |
| `TRUSTED_PROXY_COUNT` | Biasanya `1` | Bahagian di atas |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` atau lebih tinggi | Bahagian di atas |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | Semasa mula-mula menghidupkan HTTPS, cuba HSTS yang pendek (`300`) sebelum menaikkannya |
| `SESSION_LIFETIME_MINUTES` | `120` | Hayat sesi log masuk |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, zon waktu institusi | Masa pelayan dan tugas berjadual dalam UTC, skrin dalam zon waktu institusi |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | Nilai lalai | [Panduan integrasi LMS](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | Log dihantar ke output standard sebagai satu objek JSON bagi setiap baris |
| `VITE_DEV_MODE` | `false` | Produksi menggunakan output binaan (`static/dist/manifest.json`) |

## Prosedur pelaksanaan

1. Buat sandaran ([Sandaran dan pemulihan](backup-restore.md)) dan jalankan `uv run manage.py audit_verify_chain`.
2. Laksanakan kod: `git pull` (atau imej baharu), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force`: migrasi (bertukar ke sambungan `app_migrator` secara automatik), data penting disegarkan (suntingan pentadbir dikekalkan), penyegerakan katalog kebenaran. Apabila menjalankan migrasi secara berasingan, `uv run manage.py migrate` juga menggunakan `app_migrator` secara automatik. Tiada cara untuk menjalankan DDL sebagai `app_runtime`.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. Imej Docker produksi menjalankan kedua-duanya semasa binaan.
5. Mula semula proses: gunicorn `reload` (HUP), pekerja Celery (TERM membenarkan tugas yang sedang berjalan selesai; dengan `acks_late`, tugas yang terganggu dijalankan semula), Celery beat. Jalankan **tepat satu proses beat** merentas semua pelayan. Dengan dua, setiap tugas berjadual dimasukkan ke baris gilir dua kali (kunci Redis bagi setiap tugas menghalang larian serentak, bukan kemasukan berganda ke baris gilir).
6. Sahkan: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (kod keluar 0), `GET /api/v1/health/` (`ok`), log masuk ke panel pentadbiran, `uv run manage.py pdf_sample`. Pastikan dalam Flower bahawa pekerja bersambung.

## Pemeriksaan berkala

| Kekerapan | Tugas |
|---|---|
| Harian (automatik) | `audit.seal`, `lms.reconcile`, pelepasan tempat duduk pendaftaran kursus yang ditempah, kenaikan senarai menunggu, luput draf permohonan ([Tugas berjadual](scheduled-jobs.md)) |
| Mingguan | `/api/v1/health/` dan `check --deploy`, kemas kini keselamatan Python, OS dan kebergantungan (`pip-audit`), tugas yang gagal dalam Flower |
| Bulanan | `media_prune_orphans --dry-run`, latihan pemulihan sandaran, `audit_verify_chain` |
| Setiap semester | Semak semula penetapan peranan (individu yang telah meninggalkan institusi atau bertukar), pangkas rekod audit yang melepasi tempoh simpanan (`audit_prune`), sebelum pendaftaran kursus semak semula `LOGIN_RATE_LIMIT_PER_IP` dan bilangan pekerja |
