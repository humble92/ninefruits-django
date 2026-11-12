# Rujukan arahan pengurusan

- Pembaca: pengendali IT
- Skop: setiap arahan yang didaftarkan oleh aplikasi Ninefruits dalam repositori ini (`ninefruits/*/management/commands/`) dan arahan terbina dalam Django yang digunakan dalam operasi. Apabila arahan ditambah, entri `### \`command\`` juga mesti ditambah ke dokumen ini (dalam semua 16 bahasa), jika tidak CI gagal (`tests/tooling/test_command_documentation.py`).

## Konvensyen umum

Setiap arahan dijalankan sebagai `uv run manage.py {command}`. Dalam persekitaran pembangunan Docker, `docker compose exec app uv run manage.py {command}`.

| Perkara | Peraturan |
|---|---|
| Nama | `{context}:{action}` dalam sistem asal menjadi `{context}_{action}` (nama arahan Django tidak boleh mengandungi `:`). Contoh: `term:close` → `term_close` |
| Rekod audit | Arahan yang mengubah data ("Audit: direkodkan" di bawah) menulis arahan, argumen, pilihan, pengguna OS, kod keluar dan hasil ke log aktiviti (log `command`) pada setiap larian. Semaknya di bawah **Audit > Log aktiviti** dalam panel pentadbiran |
| ID larian | Setiap larian menerima ID yang bermula dengan `cmd-` sebagai ganti ID permintaan. Log aktiviti, perubahan data yang dibuat oleh larian itu dan tugas Celery yang dihantarnya semuanya membawa ID yang sama, jadi soalan "arahan manakah yang membuat perubahan ini" dijawab oleh ID tersebut. `--actor` ialah nilai yang dibekalkan oleh pengendali, jadi ia tidak dimasukkan ke dalam lajur pengguna perubahan data (pelaku sebenar ialah pengguna OS) |
| `--actor=<email>` | Sama bagi semua arahan yang diaudit. Merekodkan akaun pentadbir yang bertanggungjawab. E-mel yang tidak dikenali menghentikan larian |
| `--dry-run` | Memaparkan hasil tanpa mengubah apa-apa. Tersedia pada operasi yang sukar dibatalkan |
| `--force` | Berjalan tanpa gesaan pengesahan (untuk jadual dan skrip pelaksanaan) |
| `--reason=` | Tersedia pada arahan yang memerlukan sebab |
| Kod keluar | 0 berjaya, 1 gagal atau dibatalkan, 2 arahan semakan menemui masalah |
| Konteks pangkalan data | Semasa arahan berjalan, pelaku sesi pangkalan data ditetapkan kepada `system:command:{command}` dan muncul dalam perubahan data (trigger) |

## Arahan terbina dalam Django

### `migrate`

- Tujuan: menerapkan migrasi pangkalan data. Pembalut Ninefruits bagi arahan Django: tanpa `--database` ia menggunakan sambungan pemilik skema (`migrator`, peranan `app_migrator`). Sambungan aplikasi (`app_runtime`) tidak mempunyai keistimewaan DDL. `showmigrations` dan `sqlmigrate` juga menggunakan sambungan `migrator` secara lalai.
- Bila: semasa pemasangan pertama dan pada setiap pelaksanaan (`setup_install` juga menjalankannya).
- Pilihan: sama seperti `migrate` Django (`app_label`, `migration_name`, `--plan`, `--check`, `--database`).
- Audit: tidak direkodkan (perubahan skema disimpan dalam sejarah migrasi `django_migrations`)
- Contoh

  ```bash
  uv run manage.py migrate
  uv run manage.py migrate --plan
  ```

- Jika gagal: bagi ralat kebenaran, semak penyediaan peranan pangkalan data (`db/sql/roles/`) dalam [manual pemasangan](installation.md).

### `collectstatic`

- Tujuan: mengumpulkan output binaan Vite (`static/dist/`) serta fail statik Django dan unfold ke dalam `STATIC_ROOT` (`staticfiles/`). Pelayan web (Nginx) menyajikan direktori ini.
- Bila: pada setiap pelaksanaan, selepas `npm ci && npm run build`.
- Pilihan: `--noinput` (tanpa gesaan), `--clear` (padam fail sedia ada sebelum mengumpul).
- Audit: tidak direkodkan
- Contoh

  ```bash
  npm ci && npm run build
  uv run manage.py collectstatic --noinput
  ```

### `compilemessages`

- Tujuan: mengkompil fail terjemahan (`.po`) menjadi fail masa jalan `.mo`. Fail `.mo` tidak disimpan dalam repositori, jadi jalankan arahan ini pada setiap pemasangan dan pelaksanaan. `gettext` mesti dipasang pada sistem.
- Bila: pada setiap pelaksanaan dan selepas menyunting fail terjemahan.
- Pilihan: `--locale=` (contohnya `ko`, `zh_Hans`, `lo`), `--ignore=.venv`.
- Audit: tidak direkodkan
- Contoh

  ```bash
  uv run manage.py compilemessages --ignore=.venv
  ```

### `createsuperuser`

- Tujuan: **tidak digunakan.** Superuser Django memintas katalog peranan dan kebenaran serta jejak audit, jadi arahan ini berakhir dengan ralat (kod keluar 1) dan merujuk kepada `security_create_administrator`.
- Sebaliknya: cipta pentadbir awal dengan `security_create_administrator` (termasuk penetapan peranan pentadbir sistem dan rekod audit).
- Audit: tidak berkenaan

## Pemasangan dan demo (Fasa 1)

### `setup_install`

- Tujuan: pemasangan baharu dan kemas kini. Menjalankan secara berturutan: migrasi, data penting (templat peranan dan penyegerakan kebenaran, negara, bahasa, jenis senarai kod, jenis unit organisasi), tetapan institusi, skala gred, profil pemasangan dan pentadbir awal. Selamat dijalankan semula (data sedia ada dan nilai yang diubah oleh pentadbir dikekalkan).
- Bila: semasa pemasangan pertama dan pada setiap pelaksanaan.
- Pilihan: `--institution-name=`, `--locale=` (bahasa lalai), `--timezone=` (contohnya `Asia/Seoul`), `--profile=` (kunci profil pemasangan, boleh diulang: `korean-university`, `yust-legacy`), `--grade-scale=` (skala gred `4.5` atau `4.3`; tidak boleh diubah setelah ditetapkan; jika kosong, skala profil pertama digunakan), `--admin-email=`, `--admin-name=`, `--force` (tanpa soalan; kata laluan pentadbir dibaca daripada input standard).
- Audit: direkodkan (profil yang digunakan, sama ada pentadbir dicipta)
- Contoh

  ```bash
  uv run manage.py setup_install
  echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
      --institution-name="Demo University" --profile=korean-university \
      --admin-email=admin@example.ac.kr --admin-name="Administrator"
  ```

- Membaca output: `DONE` bagi setiap langkah. `Administrator exists` bermaksud penetapan Pentadbir Sistem sudah wujud, jadi penciptaan dilangkau.
- Jika gagal: ralat kunci tiada bermaksud `DJANGO_SECRET_KEY` dan nilai daripada `pii_generate_key` mesti ditetapkan dalam persekitaran. Kegagalan migrasi: semak peranan pangkalan data ([Pemasangan](installation.md)). `The grade scale is fixed` bermaksud `--grade-scale` berbeza daripada skala yang sudah ditetapkan.

### `setup_demo`

- Tujuan: mencipta sebuah universiti rekaan (unit organisasi, program, bangunan dan bilik, semester lepas, semasa dan berikutnya di sekitar hari ini bersama tempoh urusannya, profil universiti Korea). Memaparkan akaun demo tetap bagi setiap peranan (`registrar@demo.test` dan sebagainya, kata laluan `demo-password`). Data dalam jumlah besar dicipta dengan sisipan pukal.
- Bila: persekitaran pembangunan, latihan dan demonstrasi. **Ia tidak akan berjalan dalam produksi (`DJANGO_ENV=production`), walaupun dengan `--force`.**
- Pilihan: `--size=tiny|small|medium|large` (kira-kira 20/100/2,000/20,000 pelajar; `tiny` untuk ujian dan semakan pantas), `--seed=` (nilai yang sama menghasilkan data yang sama), `--force` (tanpa pengesahan).
- `--student-accounts`: memberikan akaun kepada setiap pelajar aktif dan menulis `load-accounts.csv` (e-mel, kata laluan) dalam storan peribadi, untuk ujian beban ([Ujian beban](load-testing.md)).
- Audit: direkodkan (saiz, benih, tempoh)
- Contoh: `uv run manage.py setup_demo --size=small --seed=42 --force`
- Jika gagal: tanpa data penting, akaun demo dilangkau (peranannya tiada); jalankan `setup_install` terlebih dahulu. Menjalankan semula pada pangkalan data yang sama melangkau data demo yang sudah wujud.

## Data rujukan dan semester (Fasa 1)

### `reference_import`

- Tujuan: mengimport data rujukan daripada CSV, dengan peraturan yang sama seperti **Import CSV** dalam panel pentadbiran (baris dipadankan mengikut kod dan dikemas kini, sel terjemahan yang kosong mengekalkan nilai sedia ada, baris yang gagal disimpan secara berasingan).
- Argumen: `type` `org_units`, `programs`, `buildings`, `rooms`, `lookup_values`, `students` (rekod pelajar), `instructors`, `courses` (versi kursus), `registration_holds` (sekatan pendaftaran) / `file` CSV UTF-8 dengan baris pengepala.
- Pilihan: `--actor=` (wajib; import direkodkan di bawah akaun ini dan hasilnya muncul pada skrin **Import CSV** akaun tersebut), `--chunk=100` (baris bagi setiap tugas Celery), `--dry-run` (semakan pengepala dan kiraan baris sahaja).
- Audit: direkodkan (jenis, nama fail, baris, nombor import, baris yang gagal)
- Format lajur: [Manual pentadbir bab 9](../admin/09-csv-import.md).
- Kod keluar: apabila tugas berjalan serta-merta (pekerja eager), hasil dipaparkan dan baris yang gagal memberikan 2. Apabila import hanya dimasukkan ke baris gilir, 0. Hasil dan CSV baris yang gagal terdapat di bawah **Data rujukan > Import CSV** dalam panel pentadbiran.
- Contoh: `uv run manage.py reference_import org_units /srv/import/org-units.csv --actor=admin@example.ac.kr --dry-run`

### `term_inspect`

- Tujuan: memaparkan semester yang sedang berjalan dan tempoh urusan yang dibuka (jenis, semester, sesi, nama, kelayakan, masa tamat) pada sesuatu masa. Digunakan untuk menyemak tetapan semester dan tempoh urusan, atau soalan seperti "mengapa pendaftaran kursus tidak dibuka?".
- Pilihan: `--at=` (lalai sekarang; contohnya `"2027-02-15 09:00"`; tanpa zon waktu, zon waktu pelayan (UTC) terpakai; `"2027-02-15 09:00 Asia/Seoul"` atau `2027-02-15T09:00+09:00` menyatakan zon).
- Audit: tidak direkodkan (baca sahaja)
- Membaca output: tarikh dinilai dalam zon waktu institusi. Tempoh urusan bagi semester berstatus dirancang atau diarkibkan tidak sekali-kali dibuka. Masa tamat dipaparkan dalam zon waktu institusi.

## Keselamatan (Fasa 0, 2)

### `security_create_administrator`

- Tujuan: mencipta akaun dengan peranan pentadbir sistem. Biasanya dipanggil oleh `setup_install`.
- Pilihan: `--email=`, `--name=`, `--password-stdin` (kata laluan daripada input standard. Wajib bagi larian bukan interaktif).
- Audit: direkodkan (ID pengguna yang dicipta)
- Contoh: `uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator"`
- Contoh (bukan interaktif): `printf '%s\n' "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator" --password-stdin`
- Jika gagal: `system_administrator role is missing` bermaksud `setup_install` mesti dijalankan terlebih dahulu. Kata laluan mesti sekurang-kurangnya 12 aksara.

### `security_sync_permissions`

- Tujuan: menyelaraskan senarai kebenaran dalam pangkalan data dengan katalog kebenaran dalam kod. Kebenaran baharu dicipta; kebenaran yang tiada dalam katalog dipadam (dan dibuang daripada setiap peranan). Peranan sistem sentiasa menerima setiap kebenaran.
- Bila: selepas pelaksanaan (`setup_install` melakukannya sebagai sebahagian daripada langkah data penting).
- Pilihan: `--dry-run` (hanya memaparkan senarai cipta/padam), `--force` (melangkau pengesahan pemadaman).
- Audit: direkodkan (kebenaran yang dicipta/dipadam)
- Membaca output: baris `create` dan `delete`. Gesaan pengesahan muncul apabila terdapat pemadaman.
- Jika gagal: menjawab "tidak" pada pengesahan akan keluar dengan kod 1 dan tidak mengubah apa-apa.

### `security_reencrypt_secrets`

- Tujuan: selepas penggiliran `DJANGO_SECRET_KEY`, menyulitkan semula dengan kunci baharu rahsia yang dilindungi oleh kunci yang diterbitkan daripadanya (rahsia TOTP aplikasi pengesah, benih kod pemulihan, rahsia klien SSO). Sehingga itu, rahsia tersebut dibaca dengan kunci sebelumnya dalam `DJANGO_SECRET_KEY_FALLBACKS`. Jalankannya sebelum membuang kunci sebelumnya ([Pengurusan kunci](security-keys.md)).
- Argumen/pilihan: `--dry-run` (hanya mengira rahsia yang masih disulitkan dengan kunci sebelumnya).
- Audit: direkodkan (kiraan)
- Membaca output: `Dry run: 0 authenticator(s) and 0 SSO client secret(s) use a previous key.` bermaksud kunci sebelumnya boleh dibuang. `cannot be decrypted` bermaksud sesuatu nilai tidak dapat dibaca dengan mana-mana kunci yang dikonfigurasi: masukkan kunci sebelumnya ke dalam `DJANGO_SECRET_KEY_FALLBACKS` dan jalankan semula.
- Contoh: `uv run manage.py security_reencrypt_secrets --dry-run`

### `security_reset_mfa`

- Tujuan: menetapkan semula pengesahan dua faktor pengguna (aplikasi pengesah, kod e-mel, kod pemulihan, peranti yang diingati). Pengguna mendaftar semula pada log masuk seterusnya. Gunakannya apabila tiada pentadbir yang dapat log masuk ke panel pentadbiran (contohnya satu-satunya pentadbir kehilangan telefon). Selain itu, gunakan **Pengguna > Set semula pengesahan dua faktor** dalam panel pentadbiran.
- Argumen/pilihan: `{user}` e-mel pengguna, `--reason=` (wajib), `--actor=` (wajib. Pentadbir yang memutuskan penetapan semula).
- Audit: direkodkan (dalam log aktiviti dan log keselamatan, bersama sebab)
- Contoh: `uv run manage.py security_reset_mfa admin@example.ac.kr --reason="Phone lost, identity verified by phone call" --actor=it-lead@example.ac.kr`

### `security_unlock_user`

- Tujuan: membuka kunci akaun yang dikunci akibat kata laluan salah berulang kali sebelum tempoh kunci tamat. Sama seperti **Pengguna > Buka kunci log masuk** dalam panel pentadbiran.
- Argumen/pilihan: `{user}` e-mel pengguna, `--reason=` (wajib).
- Audit: direkodkan (juga dalam log keselamatan)
- Membaca output: `The account is not locked.` bermaksud tiada apa-apa yang diubah.
- Catatan: ambang kunci (percubaan gagal, tempoh kunci) ditetapkan di bawah **Tetapan > Kaedah log masuk** dalam panel pentadbiran.

## Individu dan rekod pelajar (Fasa 2)

### `people_find_duplicates`

- Tujuan: menyenaraikan individu yang kelihatan seperti orang yang sama. Kriterianya ialah nombor kad pengenalan yang sama (hash carian), atau nama rumi dan tarikh lahir yang sama. Individu yang telah digabungkan dikecualikan.
- Pilihan: `--limit=100` (bilangan kumpulan yang dipaparkan).
- Audit: tidak direkodkan (baca sahaja)
- Kod keluar: 2 apabila calon pendua wujud.
- Tindakan susulan: semak setiap kumpulan di bawah **Individu** dalam panel pentadbiran dan, jika mereka orang yang sama, jalankan **Gabungkan pendua** dari halaman individu yang hendak dikekalkan. Penggabungan tidak boleh dibatalkan ([Manual pentadbir bab 14](../admin/14-merge-and-invitations.md)).
- Contoh: `uv run manage.py people_find_duplicates --limit=50`

## Kemasukan (Fasa 3)

### `admission_matriculate`

- Tujuan: mencipta rekod pelajar (nombor matrik baharu) bagi pemohon yang telah mengesahkan pendaftaran dalam sesuatu pengambilan. Sama seperti tindakan pukal **Cipta rekod pelajar** di bawah **Kemasukan > Permohonan** dalam panel pentadbiran (`MatriculateApplicant`). Setiap pemohon diproses secara berasingan, jadi satu kegagalan tidak menghentikan yang lain.
- Argumen/pilihan: `cycle` kod pengambilan, `--term=` (wajib; kod semester kemasukan, contohnya `2027-SP`; tarikh kemasukan ialah hari pertama semester), `--actor=` (wajib; akaun dengan kebenaran `Cipta rekod pelajar bagi pemohon yang diterima masuk`; hanya pemohon dalam skop akaun itu diproses), `--dry-run` (senarai sahaja).
- Audit: direkodkan (pengambilan, semester, bilangan sasaran, bilangan yang dicipta, nombor permohonan yang gagal). Setiap pemohon juga menerima entri audit urusan (`application.matriculated`).
- Kod keluar: 1 apabila kod pengambilan atau kod semester tidak dikenali atau `--actor` tiada, 2 apabila mana-mana pemohon gagal.
- Contoh: `uv run manage.py admission_matriculate DEMO-2027-REG --term=2027-SP --actor=admissions@example.ac.kr --dry-run`
- Jika gagal: `Only accepted offers without a student record ...` bermaksud pemohon sudah mempunyai rekod atau belum mengesahkan pendaftaran; `The program is not in effect on the admission date.` bermaksud program tidak sah pada tarikh kemasukan (semak tempoh sah program di bawah Data rujukan > Program); `not in your scope` bermaksud permohonan berada di luar skop akaun `--actor`.

### `admission_expire_drafts`

- Tujuan: menandakan sebagai **Luput** draf permohonan bagi pengambilan yang telah ditutup dan draf yang tidak diubah dalam tempoh yang dikonfigurasi (**Tetapan > Kemasukan > Luputkan draf yang tidak disentuh selepas (hari)**, lalai 90). Permohonan yang luput tidak lagi menghalang permohonan baharu dalam pengambilan yang sama.
- Bila: berjadual setiap hari pada 03:10 (tugas Celery beat `admission.expire_drafts` menjalankan arahan ini).
- Pilihan: `--dry-run` (kiraan sahaja).
- Audit: direkodkan (bilangan yang diluputkan)
- Contoh: `uv run manage.py admission_expire_drafts --dry-run`

## Seksyen kursus (Fasa 4)

### `section_copy`

- Tujuan: memulakan perancangan semester baharu daripada seksyen semester sebelumnya. Sama seperti **Seksyen > Salin daripada semester lain** dalam panel pentadbiran (`CopySections`). Menyalin seksyen yang tidak dibatalkan sebagai draf, bersama pensyarah (jika masih berkhidmat), waktu kelas dan bilik, peruntukan tempat duduk (masa pelepasan dianjakkan mengikut perbezaan tarikh mula semester) dan rangka kursus (sebagai draf peribadi). Versi kursus digantikan dengan versi yang berkuat kuasa pada permulaan sesi baharu.
- Argumen/pilihan: `from-term`, `to-term` kod semester (contohnya `2026-FA`), `--org-unit=` (hanya seksyen bagi kod unit organisasi ini; boleh diulang), `--dry-run` (melakukan salinan dalam transaksi dan menggulung baliknya, jadi laporannya tepat), `--actor=` (wajib. Hanya seksyen dalam skop kebenaran `Rancang seksyen` akaun itu disalin).
- Audit: direkodkan (semester sumber dan sasaran, kiraan disalin, dilangkau dan perlu disemak; salinan sebenar juga merekodkan peristiwa audit urusan `sections.copied`)
- Membaca output: `skipped` bermaksud semester sasaran sudah mempunyai kod seksyen yang sama atau tiada versi kursus yang berkuat kuasa; `note` bermaksud seksyen disalin tetapi ada sesuatu yang ditinggalkan (disalin tanpa bilik kerana bilik sudah digunakan, pensyarah yang telah bersara, dan sebagainya). Sesi dipadankan mengikut kod; jika tiada, seksyen dimasukkan ke dalam sesi semester penuh.
- Kod keluar: 1 bagi kod semester yang tidak dikenali atau `--actor` yang tiada.
- Contoh: `uv run manage.py section_copy 2026-FA 2027-FA --actor=academic@example.ac.kr --dry-run`

### `schedule_check_conflicts`

- Tujuan: menyemak seksyen sesuatu semester sebelum menerbitkan jadual waktu. Tempahan berganda bilik dan pensyarah sudah dihalang oleh pangkalan data; arahan ini mencari masalah yang dibenarkan oleh pangkalan data: kapasiti melebihi kapasiti bilik, versi kursus yang tidak berkuat kuasa pada tarikh mula sesi, pensyarah yang telah bersara, peruntukan tempat duduk melebihi kapasiti, tarikh kelas di luar sesi. Ia juga menyemak pertembungan bilik dalam data yang masuk tanpa kekangan, seperti pemulihan sandaran.
- Argumen: `term` kod semester.
- Audit: tidak direkodkan (baca sahaja)
- Kod keluar: 2 apabila terdapat masalah, 1 bagi kod semester yang tidak dikenali. Seksyen yang belum mempunyai pensyarah, bilik atau waktu kelas dipaparkan sebagai maklumat sahaja (`Note`).
- Contoh: `uv run manage.py schedule_check_conflicts 2027-SP`

## Pendaftaran kursus (Fasa 5)

### `registration_preflight`

- Tujuan: menyemak semester sebelum membuka pendaftaran kursus. Memaparkan tempoh pendaftaran kursus dan tambah/gugur, set peraturan, bilangan seksyen yang diterbitkan, seksyen dengan kapasiti 0, peruntukan tempat duduk melebihi kapasiti, versi kursus yang tidak berkuat kuasa pada tarikh mula sesi, bilangan pelajar aktif yang tidak diliputi oleh had kredit, dan bilangan pelajar yang dikenakan sekatan pendaftaran.
- Argumen: `term` kod semester (contohnya `2027-SP`).
- Audit: tidak direkodkan (baca sahaja)
- Kod keluar: 2 apabila terdapat masalah. Set peraturan yang tiada dipaparkan sebagai maklumat, bukan sebagai masalah (nilai lalai peraturan digunakan).
- Contoh: `uv run manage.py registration_preflight 2027-SP`

### `registration_simulate`

- Tujuan: memaparkan, peraturan demi peraturan, apa yang akan berlaku jika pelajar mendaftar seksyen itu sekarang (atau pada masa tertentu). Tiada apa-apa yang disimpan dan tiada percubaan direkodkan. Gunakannya untuk soalan "mengapa saya tidak boleh mendaftar?".
- Argumen: `student-number` nombor matrik, `section` `kod kursus-kod seksyen` (contohnya `CSE2010-01`).
- Pilihan: `--term=` (kod semester. Lalai ialah semester terkini yang mempunyai seksyen itu), `--at=` (masa penilaian. Contohnya `"2027-02-10 10:00 Asia/Seoul"`).
- Audit: tidak direkodkan (baca sahaja)
- Membaca output: bagi setiap peraturan, lulus/gagal, sekat/amaran dan mesejnya. Peraturan yang diliputi oleh kelulusan khas dipaparkan sebagai gagal tetapi tidak menyekat. Kapasiti dipaparkan secara berasingan di bawah jadual peraturan.
- Kod keluar: 2 apabila pendaftaran akan ditolak.
- Contoh: `uv run manage.py registration_simulate 202612345 CSE2010-01 --at="2027-02-10 10:00 Asia/Seoul"`

### `waitlist_promote`

- Tujuan: mendaftarkan pelajar dalam senarai menunggu mengikut giliran bagi seksyen yang mempunyai tempat kosong. Setiap peraturan disemak semula semasa kenaikan; entri senarai menunggu yang gagal sesuatu peraturan dibuang daripada senarai menunggu (dengan sebab direkodkan). Senarai menunggu bagi seksyen yang tempoh pendaftaran kursus dan tambah/gugurnya kedua-duanya telah ditutup akan luput. Pelajar menerima hasilnya melalui e-mel.
- Argumen/pilihan: `term?` kod semester (lalai: setiap semester yang mempunyai entri senarai menunggu), `--actor=`.
- Audit: direkodkan (kiraan seksyen, dinaikkan, dibuang, luput)
- Bila: apabila berlaku gugur, tarik diri atau pelepasan peruntukan tempat duduk, seksyen yang terjejas diproses serta-merta oleh tugas baris gilir. Arahan ini ialah jaringan keselamatan berjadual setiap jam yang mengendalikan apa-apa yang terlepas.
- Contoh: `uv run manage.py waitlist_promote 2027-SP --actor=registrar@example.ac.kr`

### `registration_release_reserved_seats`

- Tujuan: menandakan peruntukan tempat duduk yang masa pelepasannya telah berlalu (contohnya tempat yang ditempah untuk pelajar major) sebagai telah diproses dan memasukkan tugas kenaikan senarai menunggu bagi seksyen tersebut ke dalam baris gilir. Tempat yang ditempah menjadi tempat umum dalam pengiraan sebaik sahaja masa pelepasan berlalu, jadi arahan ini hanya menyerahkan tempat itu kepada senarai menunggu.
- Audit: tidak direkodkan (berjalan setiap 5 minit. Hasil kenaikan terdapat dalam rekod pendaftaran kursus)
- Bila: berjadual (setiap 5 minit, tugas Celery beat `registration.release_reserved_seats`). Tugas kenaikan ialah `registration.promote_waitlist` bagi setiap seksyen (satu demi satu bagi setiap seksyen melalui kunci Redis).
- Contoh: `uv run manage.py registration_release_reserved_seats`

## Gred (Fasa 6)

### `term_close`

- Tujuan: menutup semester. Setiap gred dalam semester mesti dimuktamadkan. Bagi setiap kelompok pelajar (100) ia mengira rekod semester (kredit, PNG dan PNGK) serta menentukan kedudukan akademik (kedudukan baik, amaran akademik, semakan pemberhentian) dan kelayakan Senarai Dekan (tugas `grading.close_term_records` dalam chord Celery); tugas penamat `grading.finish_term_close` kemudian menyusun kedudukan Senarai Dekan bagi setiap program, menutup rekod semester sebagai rekod rasmi dan menetapkan semester kepada **Gred ditutup**. Kemajuan disimpan dalam `job_batches` dan dipaparkan di atas senarai **Gred > Rekod semester**. Apabila selesai, kakitangan yang memulakannya menerima e-mel. Sama seperti **Gred > Rekod semester > Tutup semester** dalam panel pentadbiran.
- Argumen/pilihan: `term` kod semester, `--dry-run` (hanya menyemak sama ada semester boleh ditutup), `--reason=` (sebab yang disimpan dalam rekod), `--actor=`.
- Audit: direkodkan (bilangan pelajar, bilangan seksyen dengan gred yang belum dimuktamadkan, ID kelompok). Apabila penutupan selesai, rekod audit `term.closed` menyimpan kiraan amaran akademik, semakan pemberhentian dan Senarai Dekan.
- Kod keluar: 2 apabila sesetengah seksyen mempunyai gred yang belum dimuktamadkan (kiraan yang belum dimuktamadkan bagi setiap seksyen dipaparkan). 1 apabila semester tidak berstatus diterbitkan.
- Bila: selepas kemasukan gred dan pemuktamadan selesai. Ikuti kelompok dalam Flower dan pada skrin rekod semester. Tanpa pekerja Celery, status semester tidak berubah. Kelompok yang gagal dengan ralat pangkalan data dicuba semula sehingga 3 kali; jika masih gagal, kelompok kekal gagal dan semester tidak berubah (betulkan puncanya dan jalankan semula; menjalankan semula memberikan hasil yang sama).
- Contoh: `uv run manage.py term_close 2026-FA --dry-run`, `uv run manage.py term_close 2026-FA --reason="Fall 2026 grades closed" --actor=registrar@example.ac.kr`

### `grades_recalculate`

- Tujuan: mengira semula rekod semester (kredit, PNG dan PNGK) daripada gred yang telah dimuktamadkan. Gunakannya untuk menerapkan dasar penggredan yang telah diubah (tempat perpuluhan PNG, pengendalian ulang kursus) pada semester lalu. Kedudukan akademik dan Senarai Dekan mengekalkan nilai yang diputuskan semasa tutup semester. Pindaan gred yang diluluskan mengira semula pelajar itu secara automatik, jadi arahan ini tidak diperlukan untuknya.
- Pilihan: `--term=` (pelajar yang mempunyai gred dalam semester itu, dari semester itu dan seterusnya), `--student-number=` (seorang pelajar), `--reason=` (wajib), `--actor=`.
- Audit: direkodkan (bilangan pelajar, sebab)
- Kod keluar: 1 tanpa sebab, atau bagi kod semester atau nombor matrik yang tidak dikenali.
- Contoh: `uv run manage.py grades_recalculate --term=2026-SP --reason="GPA changed to three decimal places"`

### `grades_remind_missing`

- Tujuan: menghantar e-mel kepada pensyarah seksyen yang grednya belum dihantar (belum dimasukkan atau disimpan sebagai draf). Seksyen dikumpulkan mengikut pensyarah menjadi satu mesej bagi setiap seorang.
- Argumen/pilihan: `term` kod semester, `--dry-run` (memaparkan sasaran tanpa menghantar), `--actor=`.
- Audit: direkodkan (seksyen, pensyarah, mesej yang dihantar)
- Bila: beberapa hari sebelum tempoh kemasukan gred ditutup. Tambahkannya ke jadual jika perlu.
- Contoh: `uv run manage.py grades_remind_missing 2026-FA --dry-run`

## Penilaian kursus (Fasa 7)

### `evaluation_remind`

- Tujuan: menghantar e-mel kepada pelajar yang masih mempunyai kursus yang belum dinilai semasa tempoh penilaian kursus dibuka. Kursus yang berbaki dikumpulkan bagi setiap pelajar menjadi satu mesej (dalam bahasa penerima).
- Argumen/pilihan: `term` kod semester, `--dry-run` (bilangan pelajar sasaran sahaja, tiada yang dihantar), `--actor=`.
- Audit: direkodkan (pelajar sasaran, mesej yang dihantar)
- Kod keluar: 1 bagi kod semester yang tidak dikenali.
- Bila: sekali atau dua kali semasa tempoh penilaian. Tambahkannya ke jadual jika perlu.
- Contoh: `uv run manage.py evaluation_remind 2026-FA --dry-run`

### `evaluation_publish_results`

- Tujuan: menerbitkan keputusan penilaian kursus semester kepada pensyarah. Sama seperti **Penilaian kursus > Penilaian semester > Terbitkan keputusan** dalam panel pentadbiran. Walaupun selepas diterbitkan, keputusan hanya kelihatan bagi seksyen yang mencapai bilangan respons dan kadar respons minimum.
- Argumen/pilihan: `term` kod semester, `--actor=` (akaun dengan kebenaran `Urus borang penilaian, penilaian semester dan penerbitan`; direkodkan sebagai penerbit).
- Audit: direkodkan (bilangan respons, sama ada sudah diterbitkan). Audit urusan `evaluation.published`.
- Kod keluar: 1 bagi kod semester yang tidak dikenali atau semester tanpa penilaian kursus.
- Bila: selepas tempoh penilaian dan pemprosesan gred selesai. Semester yang sudah diterbitkan tidak diubah.
- Contoh: `uv run manage.py evaluation_publish_results 2026-FA --actor=academic-affairs@example.ac.kr`

## Sijil (Fasa 8)

### `certificate_verify`

- Tujuan: menyemak kod pengesahan sijil dengan kriteria yang sama seperti halaman pengesahan awam. Memaparkan jenis, nombor pengeluaran, tarikh dikeluarkan dan pemegang (bertopeng).
- Argumen/pilihan: `code` kod pengesahan (huruf besar atau kecil tidak penting).
- Audit: tiada (baca sahaja)
- Kod keluar: 0 apabila sah, 2 bagi kod yang tidak dikenali, sijil yang dibatalkan atau tempoh sah yang telah tamat.
- Contoh: `uv run manage.py certificate_verify 7Q2M9XK4TB0RWZ5C1HNA`

### `certificate_render`

- Tujuan: menjana semula PDF sijil yang telah dikeluarkan dengan data dan templat semasa, menggantikan fail yang disimpan. Sama seperti **Sijil > Sijil dikeluarkan > Jana semula** dalam panel pentadbiran. Nombor pengeluaran dan kod pengesahan kekal sama; checksum berubah. PDF dijana oleh Gotenberg.
- Argumen/pilihan: `issue` nombor pengeluaran, `--reason=` (wajib), `--actor=` (akaun dengan kebenaran `Keluarkan, jana semula dan batalkan sijil`).
- Audit: direkodkan (nombor pengeluaran, checksum baharu); audit urusan `certificate.rerendered`.
- Kod keluar: 1 tanpa sebab, bagi nombor pengeluaran yang tidak dikenali, atau apabila PDF tidak dapat dijana.
- Bila: untuk menjana semula sijil tertentu selepas membetulkan templat, ejaan nama atau `APP_URL`.
- Contoh: `uv run manage.py certificate_render ENR-2026-000001 --reason="Name spelling corrected"`

## Peperiksaan (Fasa 9)

### `assessment_import_results`

- Tujuan: memasukkan keputusan sesi peperiksaan daripada CSV. Peraturan yang sama seperti **Sesi peperiksaan > Import keputusan (CSV)** dalam panel pentadbiran (pelajar berdaftar sahaja, lulus ditentukan daripada markah, memasukkan semula sebelum penerbitan menggantikan keputusan, selepas penerbitan baris dilaporkan sebagai ralat).
- Argumen/pilihan: `type` kod jenis peperiksaan / `held_date` tarikh peperiksaan `YYYY-MM-DD` / `file` CSV UTF-8 dengan baris pengepala, `--actor=` (wajib, direkodkan sebagai orang yang memasukkan keputusan), `--dry-run` (pengesahan baris sahaja, tiada yang direkodkan).
- Format lajur: [Manual pentadbir bab 24](../admin/24-assessments.md).
- Audit: direkodkan (sesi, nama fail, kiraan baris, kiraan dimasukkan/tidak hadir/ralat). Setiap keputusan juga menerima entri audit urusan `assessment.result_recorded`.
- Kod keluar: 1 apabila sesi tidak ditemui, fail tidak dapat dibaca atau `--actor` tiada; 2 apabila terdapat baris ralat (baris lain tetap direkodkan).
- Contoh: `uv run manage.py assessment_import_results ENG_COMP 2026-05-15 storage/eng.csv --actor=registrar@example.ac.kr --dry-run`

### `assessment_publish_results`

- Tujuan: menerbitkan keputusan sesuatu sesi kepada pelajar. Sama seperti **Sesi peperiksaan > Terbitkan keputusan** dalam panel pentadbiran. Selepas penerbitan, keputusan hanya berubah melalui permohonan pembetulan.
- Argumen/pilihan: `type` kod jenis peperiksaan / `held_date` tarikh peperiksaan, `--actor=` (wajib, dengan kebenaran untuk mendaftarkan pelajar, memasukkan dan menerbitkan keputusan).
- Audit: direkodkan (sesi, bilangan keputusan) dan entri audit urusan `assessment.results_published`
- Kod keluar: 1 apabila sesi tidak ditemui, sudah diterbitkan, `--actor` tiada atau tidak mempunyai kebenaran.
- Bila: selepas kemasukan keputusan selesai.
- Contoh: `uv run manage.py assessment_publish_results ENG_COMP 2026-05-15 --actor=registrar@example.ac.kr`

## Kehadiran (Fasa 10)

### `attendance_generate_sessions`

- Tujuan: mencipta sesi kelas bagi setiap seksyen sesuatu semester daripada waktu kelasnya (hari, masa, slot masa). Sama seperti **Jana daripada waktu kelas** dalam portal pensyarah dan **Jana sesi kelas** pada tab **Sesi kelas** dalam panel pentadbiran. Sesi kelas sedia ada dan kehadirannya dikekalkan (selamat dijalankan semula). Seksyen yang dibatalkan dilangkau.
- Argumen/pilihan: `term` kod semester, `--section=` (kod kursus-kod seksyen, contohnya `CSE2010-01`, satu sahaja), `--dry-run` (bilangan seksyen sasaran sahaja), `--actor=`.
- Audit: direkodkan (semester, seksyen, sesi kelas yang dicipta)
- Bila: sebelum semester bermula, selepas waktu kelas disahkan. Jalankan semula apabila waktu kelas berubah.
- Contoh: `uv run manage.py attendance_generate_sessions 2026-FA --dry-run`

## Pengijazahan (Fasa 11)

### `degree_audit_run`

- Tujuan: menyimpan semakan syarat bergraduat bagi setiap pelajar aktif. Sama seperti **Semakan bergraduat > Jalankan semakan** dalam panel pentadbiran. Semakan terkini yang disimpan menjadi asas pemprosesan pengijazahan. Setiap larian menambah petikan (snapshot) baharu.
- Pilihan: `--term=` (kod semester tempat semakan itu dimiliki), `--student-number=` (seorang pelajar), `--min-year-level=` (hanya tahun pengajian ini dan ke atas), `--actor=`.
- Audit: direkodkan (bilangan pelajar, bilangan yang memenuhi syarat). Dengan `--actor`, audit urusan `graduation.audits_run` juga direkodkan.
- Kod keluar: 1 bagi kod semester yang tidak dikenali.
- Bila: sebelum semakan pengijazahan (akhir semester), dan selepas mengubah set syarat atau kursus setara.
- Contoh: `uv run manage.py degree_audit_run --term=2026-FA --min-year-level=4 --actor=registrar@example.edu`

## Integrasi LMS (Fasa 12)

### `lms_sync`

- Tujuan: menolak seksyen yang diterbitkan ke platform (penciptaan dan pemautan kursus, pensyarah, pelajar berdaftar). Melakukan bagi seluruh semester apa yang dilakukan oleh **Pautan kursus > Segerakkan semula** dalam panel pentadbiran. Seksyen yang sudah dipautkan hanya dipastikan semula (idempoten). Setiap langkah disimpan dalam **Log penyegerakan**.
- Argumen/pilihan: `{platform}` kod platform, `--term=` (kod semester, lalai setiap semester yang belum tamat), `--section=` (satu kod kursus-kod seksyen, contohnya `CSE2010-01`), `--dry-run` (hanya merekodkan apa yang akan dihantar sebagai "skipped"), `--actor=`.
- Audit: direkodkan (platform, seksyen, ahli, kegagalan)
- Kod keluar: 1 bagi kod platform atau kod semester yang tidak dikenali, 2 apabila mana-mana seksyen gagal (ralat bagi setiap seksyen dipaparkan).
- Bila: sebelum semester bermula, selepas platform baharu diaktifkan.
- Contoh: `uv run manage.py lms_sync DEMO --term=2026-FA --dry-run`

### `lms_reconcile`

- Tujuan: membandingkan senarai pelajar kursus di platform dengan senarai pendaftaran dalam sistem maklumat pelajar, menambah ahli yang tiada dan membuang ahli yang berlebihan. Seksyen yang belum dipautkan disegerakkan sepenuhnya. Perbezaan disimpan dalam log penyegerakan (`reconcile`, `missing` dan `extra` dalam `payload`).
- Argumen/pilihan: `{platform?}` (setiap platform aktif jika tidak dinyatakan), `--term=` (lalai semester yang belum tamat), `--dry-run` (merekodkan perbezaan sahaja), `--actor=`.
- Audit: direkodkan (seksyen bagi setiap platform, kiraan ditambah/dibuang/gagal)
- Kod keluar: 1 bagi kod platform atau kod semester yang tidak dikenali atau apabila tiada platform yang aktif, 2 apabila mana-mana seksyen gagal.
- Bila: berjadual setiap hari pada 02:30 sebagai tugas `lms.reconcile` (Celery beat). Jalankan secara manual selepas gangguan platform.

### `api_issue_token`

- Tujuan: mengeluarkan token integrasi API bagi sesuatu akaun ([ADR 0004-django](../../../../porting/decisions/0004-django-api-tokens.md)), biasanya akaun perkhidmatan dengan kebenaran yang diperlukan sahaja (LMS: `lms.manage`, BI: `reports.view`). Token dipaparkan **sekali**, pada baris pertama output standard; pangkalan data hanya menyimpan cernaannya (digest). Permintaan menghantarnya dalam pengepala `Authorization: Token <token>`.
- Argumen/pilihan: `{email}` e-mel akaun, `--days=` (hayat 1 hingga 365 hari, lalai `API_TOKEN_TTL_DAYS` = 90), `--reason=` (tujuannya, direkodkan dalam audit), `--actor=`.
- Audit: direkodkan (`api.token_issued`: awalan kunci dan masa luput; tidak sekali-kali token itu sendiri)
- Kod keluar: 1 bagi akaun yang tidak dikenali atau tidak aktif atau hayat di luar julat.
- Contoh: `uv run manage.py api_issue_token moodle-sync@example.ac.kr --days=365 --reason="Moodle callbacks" --actor=admin@example.ac.kr`

### `api_revoke_tokens`

- Tujuan: membatalkan token API sesuatu akaun (semua, atau satu dengan `--key=`). `--list` hanya menyenaraikan token (awalan kunci, masa dikeluarkan dan masa luput).
- Argumen/pilihan: `{email}`, `--key=` (awalan kunci), `--list`, `--reason=`, `--actor=`.
- Audit: direkodkan (`api.token_revoked`: awalan kunci yang dibatalkan)
- Kod keluar: 1 bagi akaun yang tidak dikenali atau tiada token dengan `--key` tersebut.
- Bila: apabila sesuatu integrasi tamat, token mungkin telah bocor, atau orang yang bertanggungjawab bertukar.

## Pemeriksaan operasi dan pembersihan (Fasa 13)

### `system_health_check`

- Tujuan: memeriksa konfigurasi dan kunci (`DJANGO_SECRET_KEY`, kunci PII, `DEBUG`), sambungan dan peranan pangkalan data (runtime, migrator, reporting), RLS pada jadual data peribadi, migrasi yang belum dijalankan, penyegerakan katalog kebenaran, Redis, pekerja Celery, Gotenberg, penulisan storan peribadi dan denyutan beat (`core.heartbeat`, dalam tempoh 5 minit).
- Pilihan: `--json` (output untuk pemantauan).
- Audit: tiada (baca sahaja)
- Kod keluar: 2 apabila mana-mana pemeriksaan gagal.
- Bila: sejurus selepas pelaksanaan, apabila gangguan disyaki, secara berkala daripada sistem pemantauan. Pengimbang beban menggunakan `/api/v1/health/`.
- Contoh

  ```bash
  uv run manage.py system_health_check
  uv run manage.py system_health_check --json
  ```

### `audit_seal`

- Tujuan: memautkan baris baharu jadual audit (`audit.record_changes`, `audit.activity_log`, `audit.security_events`) ke dalam rantaian hash ([Integriti audit](audit-and-maintenance.md)). Berjalan pada sambungan pemilik skema (`migrator`).
- Pilihan: `--table=` (salah satu daripada record_changes, activity_log, security_events; boleh diulang), `--actor=`.
- Audit: direkodkan (baris yang dimeterai bagi setiap jadual)
- Bila: berjadual setiap hari pada 03:30.
- Contoh

  ```bash
  uv run manage.py audit_seal
  uv run manage.py audit_seal --table=activity_log
  ```

### `audit_verify_chain`

- Tujuan: mengira semula hash kandungan dan rantaian baris audit untuk mengesan pengubahan tanpa kebenaran, pemadaman dan penyusunan semula. Memaparkan, bagi setiap jadual, baris yang disemak, baris yang dimeterai, ketidakpadanan dan ID pertama yang tidak sepadan.
- Pilihan: `--table=`.
- Audit: tiada (baca sahaja)
- Kod keluar: 2 apabila terdapat ketidakpadanan.
- Bila: sebelum sandaran, semasa semakan keselamatan, selepas pemangkasan.

### `audit_prune`

- Tujuan: memadam baris audit yang **telah dimeterai** dan melepasi tempoh simpanan. Berjalan pada sambungan pemilik skema dalam transaksi dengan `app.audit_maintenance = on`. Baris yang belum dimeterai dikekalkan (jalankan `audit_seal` terlebih dahulu). Setiap pemadaman merekodkan peristiwa keselamatan `audit.pruned` (jadual, tarikh potong, baris yang dipadam, julat ID, `chain_hash` baris sempadan).
- Pilihan: `--before=YYYY-MM-DD` (wajib; baris sebelum tengah malam hari tersebut), `--table=`, `--dry-run` (kiraan sahaja), `--actor=`.
- Audit: direkodkan (tarikh potong, baris yang dipadam dan julat ID bagi setiap jadual)
- Bila: mengikut dasar tempoh simpanan, selepas sandaran.
- Contoh

  ```bash
  uv run manage.py audit_prune --before=2023-03-01 --dry-run
  uv run manage.py audit_prune --before=2023-03-01 --table=record_changes --actor=ops@example.edu
  ```

### `media_prune_orphans`

- Tujuan: memadam baris media yang pemiliknya sudah tiada dan direktori (`<media id>/`) pada storan peribadi tanpa baris (foto individu, dokumen permohonan, PDF sijil, bukti peperiksaan).
- Pilihan: `--dry-run` (senarai sahaja), `--actor=`.
- Audit: direkodkan (baris, direktori)
- Bila: setiap bulan atau selepas pemadaman pukal.

## Kunci penyulitan data peribadi (Fasa 0)

### `pii_generate_key`

- Tujuan: memaparkan kunci baharu (32 bait, `base64:...`) untuk `PII_ENCRYPTION_KEY` dan `PII_HASH_KEY`. Tidak menyimpan apa-apa.
- Audit: tidak direkodkan
- Amaran: mengubah `PII_HASH_KEY` menjadikan setiap hash carian (`*_hash`) tidak sah. Giliran kunci penyulitan sahaja: pindahkan kunci lama ke `PII_PREVIOUS_KEYS`, kemudian jalankan `pii_reencrypt`.
- Contoh

  ```bash
  uv run manage.py pii_generate_key
  ```

### `pii_reencrypt`

- Tujuan: selepas penggiliran kunci, menyulitkan semula data peribadi yang disulitkan dengan kunci sebelumnya menggunakan kunci semasa. Berjalan sebagai kumpulan tugas Celery ke atas kelompok rekod. Rekod yang sudah menggunakan kunci semasa tidak disentuh.
- Argumen: model yang mempunyai medan data peribadi yang disulitkan (`app_label.Model`, contohnya `person.Person`).
- Pilihan: `--chunk=500` (rekod bagi setiap tugas), `--dry-run` (hanya mengira rekod yang menggunakan kunci sebelumnya), `--force` (tanpa pengesahan), `--actor=`.
- Audit: direkodkan (ID kelompok, bilangan tugas / kiraan pratonton)
- Pengesahan: ikuti tugas dalam Flower. Apabila selesai dan `--dry-run` melaporkan 0, buang kunci sebelumnya daripada `PII_PREVIOUS_KEYS`.
- Contoh

  ```bash
  uv run manage.py pii_reencrypt person.Person --dry-run
  uv run manage.py pii_reencrypt person.Person --force --actor=ops@example.edu
  ```

## Penyetempatan (Fasa 0)

### `i18n_missing`

- Tujuan: mengekstrak rentetan yang boleh diterjemah daripada sumber seperti yang dilakukan oleh `makemessages` (tanpa menulis fail), membandingkannya dengan setiap katalog (`locale/` global dan `locale/` setiap aplikasi) dan menyenaraikan, bagi setiap bahasa, rentetan yang tiada (tiada dalam katalog, `msgstr` kosong, fuzzy, pemegang tempat yang berbeza) dan entri usang.
- Argumen/pilihan: `[locale]` (satu bahasa sahaja, contohnya `ko`, `zh-hans`, `lo`), `--strict` (kod keluar 2 apabila terdapat rentetan yang tiada; digunakan dalam CI), `--no-extract` (semak katalog sahaja, tanpa imbasan sumber).
- Audit: tidak direkodkan
- Keperluan: GNU gettext (`xgettext`, `msguniq`).
- Contoh

  ```bash
  uv run manage.py i18n_missing --strict
  uv run manage.py i18n_missing lo
  ```

### `i18n_export`

- Tujuan: menulis helaian untuk penterjemah (`.xlsx` atau `.csv`, dipilih mengikut sambungan fail). Lajur: `catalog` (lokasi katalog), `context`, `source` (msgid bahasa Inggeris), `source_plural`, `translation`, `note` (kunci asal).
- Argumen/pilihan: `{locale} {path}`, `--missing` (hanya rentetan tanpa terjemahan).
- Audit: tidak direkodkan
- Contoh: `uv run manage.py i18n_export ko storage/ko.xlsx --missing`

### `i18n_import`

- Tujuan: menulis semula helaian yang diisi oleh penterjemah ke dalam katalog (`.po`) dan mengkompilnya (`.mo`). Hanya rentetan yang wujud dalam katalog (katalog, konteks dan teks bahasa Inggeris yang sama) diimport; terjemahan yang kosong dilangkau.
- Argumen/pilihan: `{locale} {path}`, `--dry-run` (menyenaraikan rentetan yang akan ditulis), `--actor=`.
- Audit: direkodkan (bahasa, bilangan terjemahan)
- Catatan: katalog berada dalam repositori. Commit perubahan `.po` selepas mengimport.

### `i18n_makemessages`

- Tujuan: menjalankan `makemessages` dari akar repositori supaya setiap katalog sepadan dengan sumber (ko, zh_Hans, lo). Rentetan dimasukkan ke dalam `locale/` aplikasi jika aplikasi itu mempunyainya, jika tidak ke dalam `locale/` global. `.venv`, `tests`, `docs` dan direktori seumpamanya dilangkau.
- Pilihan: seperti `makemessages` Django (`-l`, `--no-obsolete`, ...).
- Audit: tidak direkodkan
- Contoh: `uv run manage.py i18n_makemessages`

## Semakan (Fasa 0)

### `pdf_sample`

- Tujuan: menjana jadual yang mencampurkan tulisan Hangul, CJK, Lao, Thai, Devanagari, Cyrillic dan Latin ke PDF untuk menyemak fon dan sambungan ke perkhidmatan PDF (Gotenberg).
- Argumen: `[path]` (lalai `pdf-sample.pdf`, relatif kepada storan fail peribadi `PRIVATE_MEDIA_ROOT`).
- Audit: tidak direkodkan
- Jika gagal: kod keluar 1. Bagi ralat sambungan, semak `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` dan kontena Gotenberg.
- Contoh: `uv run manage.py pdf_sample`

### `naming_check`

- Tujuan: menyemak skema pangkalan data dan sumber berdasarkan [konvensyen penamaan](../../../development/naming.md). Ia menyemak nama jadual dan lajur dalam katalog pangkalan data sebenar (skema `public`, `audit`, `reporting`), nama fail migrasi aplikasi Ninefruits, nama arahan pengurusan (`context_action`) serta msgid dan msgctxt dalam katalog terjemahan (`.po`).
- Peraturan: snake_case, akhiran terlarang (`_old`, `_new`, `_backup`, `_tmp`, tarikh, nombor), nama yang mengandungi kod bahasa, lajur masa tanpa zon waktu (`timestamp without time zone`), nama lajur boolean (`is_`, `has_`, `can_` atau kata kerja), nama lajur tarikh (`_date`), msgid yang berbentuk kunci semantik (`registration.errors.x`). Jadual yang ditakrifkan oleh Django dan pakej (`django_*`, allauth, Celery beat, `settings`, `cache`, `jobs`, `media` dan sebagainya) dikecualikan.
- Pilihan: `--database=` (sambungan pangkalan data yang disemak, lalai `default`), `--skip-database` (semakan fail sahaja, tanpa pangkalan data).
- Audit: tidak direkodkan
- Kod keluar: 2 apabila masalah ditemui.
- Contoh

  ```bash
  uv run manage.py naming_check
  ```
