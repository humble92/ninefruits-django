# Ujian beban (puncak pendaftaran kursus)

- Pembaca: pengendali IT
- Berkaitan: [Senarai semak pelaksanaan](deployment-checklist.md), [Pemasangan](installation.md), [Arahan](commands.md)

Locust menghasilkan semula pagi pertama pendaftaran kursus, apabila ramai pelajar berebut seksyen yang sama serentak. Skripnya ialah `loadtest/registration.py` (`tests/load/registration.js` k6 dalam sistem asal), pembantu larian ialah `loadtest/run.sh`, dan semakan pendaftaran melebihi kapasiti ialah `loadtest/seat_check.sql`.

[Kandungan manual](../README.md)

## Penyediaan

1. Cipta pangkalan data khusus untuk ujian beban (jangan sekali-kali pangkalan data produksi). Peranan dan pangkalan data dicipta seperti dalam bahagian 2 [Pemasangan](installation.md); kemudian pasang dan muatkan demo besar. Senarai akaun pelajar ditulis ke `load-accounts.csv` dalam storan peribadi (`PRIVATE_MEDIA_ROOT`, lalai `storage/private`).

   ```bash
   export DB_DATABASE=nf_load
   uv run manage.py setup_install --profile=korean-university --grade-scale=4.5 --force < /dev/null
   uv run manage.py setup_demo --size=large --seed=42 --student-accounts --force
   ```

2. Tempoh urusan pendaftaran kursus mesti dibuka. Demo mencipta tempoh pendaftaran kursus semester berikutnya mengikut tahun pengajian (tahun 4 sudah dibuka, tahun 3 dalam dua hari, tahun 1 dan 2 dalam tiga hari). Untuk mengukur dengan semua tahun, anjakkan permulaan tempoh pendaftaran kursus yang lain ke masa lalu di bawah **Tempoh urusan** pada halaman **Sunting** semester ([Manual pentadbir bab 10](../admin/10-terms.md)), atau jalankan ini sebagai superuser dalam pangkalan data ujian:

   ```sql
   UPDATE term_windows SET opens_at = now() - interval '1 hour'
    WHERE window_type = 'registration' AND opens_at > now() AND closes_at > now();
   ```

3. Redis dan pekerja Celery mesti berjalan. Tempat duduk diputuskan terus dalam pangkalan data, tetapi kenaikan senarai menunggu, penyegerakan LMS dan pemberitahuan melalui baris gilir. Jika Redis dikongsi dengan kerja lain, gunakan nombor pangkalan data yang lain, contohnya `REDIS_URL=redis://127.0.0.1:6379/7`.

## Menjalankan

`loadtest/run.sh` memulakan gunicorn (`config/gunicorn.py`) dan pekerja Celery, menjalankan Locust tanpa antara muka, menjalankan semakan tempat duduk dan menghentikan semuanya.

```bash
export DB_DATABASE=nf_load DB_POOL=true DB_POOL_MIN=1 DB_POOL_MAX=2 DB_PREPARE_THRESHOLD=2
WORKERS=9 USERS=100 DURATION=1m loadtest/run.sh storage/loadtest/w9-u100
```

Untuk menjalankannya secara manual, mulakan pelayan dengan `TRUSTED_PROXY_COUNT=1` dan jalankan Locust:

```bash
TRUSTED_PROXY_COUNT=1 DJANGO_DEBUG=false GUNICORN_WORKERS=9 uv run gunicorn config.wsgi -c config/gunicorn.py
uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \
    --host http://127.0.0.1:8000 --csv storage/loadtest/run
psql -h 127.0.0.1 -U postgres -d nf_load -v term=<term id> -f loadtest/seat_check.sql
```

- Senario: log masuk (`/accounts/login/`) → halaman pendaftaran kursus → carian kursus (HTMX `?partial=results`) → daftar seksyen pertama yang mempunyai tempat kosong → gugurkannya. Setiap lelaran mengosongkan kuki dan log masuk sebagai pelajar seterusnya. Seksyen penuh dan penolakan peraturan dikira sebagai hasil biasa (`registration outcomes`).
- Butang daftar dan gugur menghantar seperti HTMX (`HX-Request`); pelayan menjawab 302 ke halaman pendaftaran kursus. Masa `enroll` dan `drop` termasuk halaman tersebut (pelayar memerlukannya sebelum menukar `#registration`).
- Setiap pelajar menghantar alamat `X-Forwarded-For` sendiri. Dengan pelayan di sebalik satu lompatan proksi (`TRUSTED_PROXY_COUNT=1`), had log masuk bagi setiap alamat oleh allauth terpakai bagi setiap alamat pelajar, seperti di kampus sebenar. `ADDRESSES=1` menghasilkan semula keadaan setiap pelajar di sebalik satu alamat (NAT).
- Persekitaran: `ACCOUNTS` (CSV akaun), `SEARCH` (teks carian, lalai `GEN`), `ADDRESSES`, `FIRST_ACCOUNT` (akaun pertama, rawak secara lalai). `run.sh` menerima `WORKERS`, `USERS`, `SPAWN_RATE`, `DURATION`, `TERM_ID`, `PORT`.
- Naikkan `USERS` daripada 100 ke 200 hingga 500 dan perhatikan p95 bagi setiap halaman serta kadar kegagalan. Ambang: p95 halaman pendaftaran kursus < 800 ms, p95 pendaftaran < 1.5 s, kegagalan < 1 %. Locust keluar dengan kod 1 apabila sesuatu ambang gagal.
- Di sebelah pelayan, perhatikan bilangan sambungan dan penantian kunci dalam `pg_stat_activity` (`wait_event_type = 'Lock'`), tunggakan Celery dan ketepuan CPU. Locust pada pelayan yang sama turut menggunakan CPU, jadi angka tersebut ialah had bawah.

## Perkara yang dijamin oleh reka bentuk

- Kapasiti dilindungi oleh kunci baris seksyen (`SeatAllocator.lock`, `SELECT ... FOR NO KEY UPDATE`) dan kekangan CHECK, jadi permintaan serentak tidak sekali-kali menyebabkan seksyen melebihi kapasiti (`tests/registration/test_concurrent_registration.py`: 16 proses, 5 tempat duduk). Kunci ini hanya membuatkan permintaan tempat duduk bagi seksyen yang sama saling menunggu; ia tidak menyekat semakan kunci asing bagi baris yang sekadar merujuk seksyen tersebut (percubaan pendaftaran kursus, log penyegerakan LMS).
- Selepas larian, empat pertanyaan dalam `loadtest/seat_check.sql` mesti tidak mengembalikan sebarang baris (melebihi kapasiti, ketidakpadanan pembilang tempat duduk, kumpulan tempat duduk melebihi kapasiti, pendaftaran berganda dalam seksyen).
- Bilangan pertanyaan halaman pendaftaran kursus tidak bertambah mengikut bilangan pendaftaran, entri senarai menunggu atau hasil carian (`tests/registration/test_portal_query_count.py`).

## Had log masuk bagi setiap alamat dan proksi

Selain had kegagalan bagi setiap akaun (5 seminit), allauth mengenakan **had log masuk bagi setiap alamat** (`LOGIN_RATE_LIMIT_PER_IP`, lalai `30/m/ip`), yang tidak wujud dalam sistem asal. Alamat yang dilihat oleh aplikasi ditentukan oleh `TRUSTED_PROXY_COUNT` (`ninefruits.core.http.client_ip`).

- Di sebalik Nginx dengan `TRUSTED_PROXY_COUNT=0` (lalai), setiap permintaan mempunyai alamat Nginx. Kampus yang keluar melalui satu alamat NAT ialah kes yang sama.
- Larian yang menghasilkan semula keadaan ini (`ADDRESSES=1`, 100 VU, 1 minit): daripada 4,876 log masuk, **hanya 30 berjaya** dan 4,846 ditolak dengan 429 (49 % kegagalan). Hanya 20 pendaftaran berjaya dalam minit tersebut. Dengan satu alamat bagi setiap pelajar dalam keadaan yang sama, tiada log masuk ditolak.
- Tetapan produksi: tetapkan `TRUSTED_PROXY_COUNT` kepada bilangan proksi (`1` bagi satu Nginx). Jika kebanyakan pelajar berkongsi satu alamat NAT, naikkan `LOGIN_RATE_LIMIT_PER_IP` kepada kadar log masuk puncak. Contoh: 2,000 pelajar log masuk dalam 10 minit bermaksud 200 seminit dari satu alamat, jadi `300/m/ip`. Nilai kosong membuang had bagi setiap alamat (seperti dalam sistem asal; had kegagalan bagi setiap akaun kekal).

## Keputusan konfigurasi pelayan

- **Pekerja segerak gunicorn** (`config/gunicorn.py`). `GUNICORN_WORKERS` secara lalai ialah teras CPU × 2 + 1. Daya pemprosesan dihadkan oleh CPU: pada 4 teras, 4, 9 dan 16 pekerja memberikan daya pemprosesan yang sama (23 hingga 26 permintaan sesaat). Pekerja tambahan hanya menambah sambungan pangkalan data (12 → 36) dan penantian kunci (puncak 1 → 12). Jangan melebihi teras × 2 + 1; skalakan secara mendatar dengan lebih banyak pelayan aplikasi.
- **Kolam sambungan dan pernyataan tersedia**: `DB_POOL=true`, `DB_POOL_MIN=1`, `DB_POOL_MAX=2`, `DB_PREPARE_THRESHOLD=2`. Disebabkan dasar keselamatan peringkat baris (RLS), perancangan pertanyaan merupakan sebahagian besar masa pangkalan data bagi sesuatu halaman (31 pertanyaan halaman pendaftaran kursus: 51 ms perancangan, 19 ms pelaksanaan). Menggunakan semula sambungan dan menyediakan pernyataan dengan pengikatan di sebelah pelayan merancang setiap pertanyaan sekali bagi setiap sambungan. Pada 4 teras yang sama, daya pemprosesan meningkat daripada 16.8 kepada 25.6 permintaan sesaat, dan median halaman pendaftaran kursus bagi seorang pengguna daripada 160 ms kepada 97 ms. Sesebuah pelayan memerlukan pekerja × `DB_POOL_MAX` + keserentakan Celery sambungan, di bawah `max_connections` PostgreSQL. Di sebalik PgBouncer dalam mod transaksi, pernyataan tersedia tidak boleh digunakan: kekalkan `DB_PREPARE_THRESHOLD=0`. Keseluruhan suite ujian (1,066 ujian) lulus dengan tetapan ini.
- **ASGI (keputusan Octane dalam sistem asal)**: tidak diguna pakai. Setiap halaman ialah paparan segerak, yang akan dijalankan oleh ASGI dalam satu thread tanpa faedah, dan daya pemprosesan mengikut bilangan teras CPU. Django tidak memulakan semula aplikasi bagi setiap permintaan (tidak seperti PHP-FPM), jadi faedah yang diberikan oleh Octane sudah ada; faedah sambungan berterusan datang daripada kolam dan pernyataan tersedia di atas.
- Log masuk menggunakan banyak CPU bagi setiap permintaan kerana semakan hash Argon2 (kira-kira 140 ms dengan seorang pengguna). Apabila log masuk bertimbun pada waktu puncak, kos ini yang pertama sekali menghakis daya pemprosesan.

## Ukuran pada 2026-10-24

Persekitaran: 4 vCPU (Xeon 2.1 GHz, `nproc` = 4), RAM 15 GB, mesin pembangunan yang dikongsi dengan kerja lain (larian ujian; purata beban 7 hingga 21 semasa pengukuran), dengan Locust, gunicorn, PostgreSQL 18 dan Redis pada mesin yang sama. Python 3.14, Django 6.1, gunicorn 26.2, `DJANGO_DEBUG=false`. Demo `--size=large --seed=42` (20,004 pelajar, 11,437 akaun pelajar, dicipta dalam 416 saat), tempoh pendaftaran kursus musim bunga 2027 dibuka bagi semua tahun, 52 seksyen diterbitkan (2,262 tempat duduk). Satu minit setiap larian, `TRUSTED_PROXY_COUNT=1`, satu alamat bagi setiap pelajar.

| Keadaan | Daya pemprosesan | p95 halaman | p95 pendaftaran | Kegagalan | Didaftarkan / ditolak | Maks. sambungan PG |
|---|---|---|---|---|---|---|
| 2 VU, 9 pekerja, tanpa kolam | 5.1 req/s | 200 ms | 640 ms | 0 / 300 | 50 / 0 | 3 |
| 2 VU, 9 pekerja, kolam + pernyataan tersedia | 6.2 req/s | 160 ms | 470 ms | 0 / 372 | 62 / 0 | 22 |
| 100 VU, 4 pekerja, tanpa kolam | 16.8 req/s | 6.0 s | 11 s | 0 / 1,005 | 52 / 86 | 6 |
| 100 VU, 16 pekerja, tanpa kolam | 17.1 req/s | 6.1 s | 11 s | 0 / 1,027 | 60 / 86 | 18 |
| 100 VU, 4 pekerja, kolam + pernyataan tersedia | 25.6 req/s | 4.1 s | 7.0 s | 0 / 1,536 | 97 / 155 | 12 |
| 100 VU, 9 pekerja, kolam + pernyataan tersedia | 25.4 req/s | 4.5 s | 7.3 s | 0 / 1,523 | 77 / 167 | 22 |
| 100 VU, 16 pekerja, kolam + pernyataan tersedia | 23.4 req/s | 4.6 s | 8.4 s | 0 / 1,405 | 131 / 79 | 36 |
| 200 VU, 9 pekerja, kolam + pernyataan tersedia | 29.8 req/s | 9.4 s | 14 s | 0 / 1,792 | 66 / 172 | 22 |
| 200 VU, 16 pekerja, kolam + pernyataan tersedia | 29.2 req/s | 9.1 s | 14 s | 0 / 1,761 | 53 / 174 | 36 |
| 100 VU, 9 pekerja, satu alamat (NAT) | (kebanyakannya 429) | 2.0 s | 3.3 s | 4,846 / 9,862 | 20 / 10 | 22 |

Cara membacanya

- Tiada kegagalan HTTP dalam mana-mana larian (kecuali larian satu alamat) dan tiada pendaftaran melebihi kapasiti (`seat_check.sql` tidak mengembalikan sebarang baris). Penolakan ialah seksyen penuh (`capacity`) dan kursus berganda (`duplicate_course`, pendaftaran yang ditinggalkan oleh lelaran yang terputus pada akhir larian sebelumnya): tingkah laku biasa.
- Kelewatan beberapa saat pada 100 VU ialah giliran permintaan. Dengan seorang pengguna, pelayan mengendalikan halaman dalam kira-kira 100 ms dan satu pendaftaran (POST ditambah halaman yang dikembalikan) dalam kira-kira 290 ms; mesin ini, yang berkongsi 4 teras antara Locust, PostgreSQL dan kerja lain, mencapai maksimum 25 hingga 30 permintaan sesaat. Pada mesin ini ambang (p95 halaman < 800 ms, p95 pendaftaran < 1.5 s) tidak dicapai pada 100 VU.
- Penantian kunci hanya datang daripada kunci tempat duduk bagi seksyen yang sama dan adalah singkat (puncak seketika 1 hingga 12, lebih tinggi dengan lebih banyak pekerja). Sambungan pangkalan data kekal pada atau di bawah pekerja × 2.
- Dengan mengambil puncak pendaftaran kursus sebagai "2,000 pelajar membuat 6 permintaan setiap seorang dalam 10 minit", kita mendapat 20 permintaan sesaat. Mesin ini (kolam + pernyataan tersedia) mencapai 25 hingga 30, jadi pelayan aplikasi khusus 8 teras mempunyai ruang lebihan. Sebelum operasi sebenar bermula: jalankan skrip yang sama pada 200 dan 500 VU dalam persekitaran staging yang dikonfigurasi seperti produksi (pelayan aplikasi khusus, Nginx, pelayan pangkalan data berasingan, Locust pada mesin lain) dan sahkan ambang tersebut.
- Sistem asal (Laravel, kontena pembangunan Sail, pelayan terbina dalam) mencapai 24.7 req/s dengan 4 pekerja dan 34.5 req/s dengan 16 pekerja pada 100 VU. Mesinnya berbeza, jadi angka tersebut tidak boleh dibandingkan secara langsung.
