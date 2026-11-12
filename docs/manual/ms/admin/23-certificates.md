# 23. Sijil

Menu: **Sijil > Sijil dikeluarkan**, **Sijil > Jenis sijil**, **Tetapan > Tetapan sijil**. Sijil dikeluarkan dengan butang **Keluarkan sijil** pada skrin rekod pelajar (**Pelajar dan kakitangan > Rekod pelajar**, buka sesuatu rekod). Pelajar memuat turun PDF sijil mereka sendiri dalam portal di bawah **Sijil**. Sesiapa sahaja boleh mengesahkan sijil pada halaman `/verify/{code}/`.

| Kebenaran | Apa yang dibenarkan |
|---|---|
| `Keluarkan, jana semula dan batalkan sijil` | Mengeluarkan, menjana semula, membatalkan, melihat sijil yang dikeluarkan (dalam skop paparan rekod pelajar) |
| `Urus jenis sijil, templat dan tetapan` | Jenis dan templatnya bagi setiap bahasa, corak nombor siri, penandatangan |

Lalai peranan: Pegawai Sijil mengeluarkan, Pegawai Pendaftar mempunyai kedua-duanya, Pegawai Hal Ehwal Akademik mengurus jenis dan templat. Berikan kebenaran pengeluaran dengan **skop global** (dasar pangkalan data hanya menerima pemberian global); pelajar yang boleh dikeluarkan sijil oleh seseorang kakitangan mengikut skop paparan rekod pelajarnya. Contohnya, berikan pegawai sijil sesebuah fakulti `Keluarkan, jana semula dan batalkan sijil` secara global dan `Lihat rekod pelajar` bagi fakulti tersebut.

## Perbezaan daripada sistem lama

- **Daftar sijil yang dikeluarkan.** Sistem lama (YUSTIC) mencetak terus daripada skrin (`aca3/cti_*`), dan daftarnya (`SRCERT`) wujud hanya untuk menjana nombor, jadi ia tidak menunjukkan siapa yang mengeluarkan sijil atau sama ada ia telah dibatalkan. Sistem baharu merekodkan nombor siri, kod pengesahan, kakitangan, tujuan, bilangan salinan, fail PDF dan checksum bagi setiap pengeluaran, dan sijil yang dibatalkan mengekalkan barisnya.
- **Pengesahan.** Sistem lama tiada pengesahan. Setiap sijil membawa kod pengesahan dan kod QR, dan halaman awam menunjukkan bahawa ia telah dikeluarkan, jenisnya, tarikh pengeluaran dan pemegang yang disamarkan (aksara pertama dan terakhir nama, 4 aksara pertama nombor matrik).
- **Templat.** Sistem lama mempunyai skrip PDF berasingan bagi setiap jenis dan bahasa. Sistem baharu menyunting templat bagi setiap bahasa (tajuk, kandungan, pengaki, penandatangan) untuk setiap jenis pada skrin.
- **Sekatan.** Sistem lama mengeluarkan sijil tanpa mengira senarai penafian pendaftaran. Sistem baharu tidak mengeluarkan sijil kepada pelajar yang mempunyai sekatan sijil ([bab 20](20-registration.md)).
- Yuran tidak direkodkan (sistem lama hanya merekodkan jumlah).
- Tiada permohonan dalam talian oleh pelajar (pelan pemindahan 17.5). Kakitangan mengeluarkan sijil.

## Jenis dan templat

**Jenis sijil**: kod (digunakan dalam nombor siri), nama (mengikut bahasa), sasaran (semua rekod pelajar / pelajar (belum bergraduat) / graduan), termasuk gred, termasuk foto, aktif, susunan. Profil universiti Korea (`setup_install --profile=korean-university`) menyemai tiga jenis beserta templat dalam empat bahasa (Korea, Inggeris, Cina Ringkas, Lao). Ia tidak menambah apa-apa sebaik sahaja sebarang jenis wujud, jadi suntingan anda kekal.

| Kod | Jenis | Sasaran | Catatan |
|---|---|---|---|
| `ENR` | Surat Pengesahan Pelajar | Pelajar (belum bergraduat) | |
| `GRD` | Surat Pengesahan Tamat Pengajian | Graduan | Tarikh bergraduat, nombor ijazah |
| `TRN` | Transkrip Akademik | Semua rekod pelajar | Jadual gred muktamad mengikut semester, PNGK dan kredit diperoleh |

**Templat** (bahagian **Templat** di bawah skrin suntingan jenis): satu bagi setiap bahasa. Bahasa, tajuk, kandungan (perenggan dipisahkan oleh baris kosong), pengaki, penandatangan. Kandungan menggunakan pemegang tempat dalam tanda kurung kerinting.

| Pemegang tempat | Nilai |
|---|---|
| `{institution}` | Nama institusi (dalam bahasa tersebut) |
| `{student_name}`, `{student_number}` | Nama (dalam bentuk bahasa tersebut, jika tidak ejaan Rumi), nombor matrik |
| `{program}`, `{org_unit}` | Program, unit organisasi |
| `{admission_date}`, `{graduation_date}`, `{degree_number}` | Tarikh kemasukan, tarikh bergraduat, nombor ijazah |
| `{status}`, `{year_level}` | Status pelajar, tahun pengajian |
| `{birth_date}`, `{gender}`, `{nationality}` | Tarikh lahir, jantina, kewarganegaraan |
| `{issue_date}`, `{serial_number}`, `{purpose}`, `{copies}` | Tarikh pengeluaran, nombor siri, tujuan, bilangan salinan |

Tarikh dicetak dalam format bahasa tersebut (cth. `October 24, 2026`, `2026년 10월 24일`). Nilai yang tiada (cth. tarikh bergraduat) dicetak sebagai kosong; pemegang tempat yang tiada dalam senarai kekal seperti yang ditulis. Jadual maklumat peribadi (nama, nombor matrik, tarikh lahir, jantina, kewarganegaraan, program, tarikh kemasukan, kemudian tarikh bergraduat bagi graduan atau status dan tahun pengajian bagi yang lain) ditambah secara automatik di atas kandungan. Keseluruhan sijil (label jadual, tarikh, status) dicetak dalam bahasa templat.

## Tetapan

**Tetapan > Tetapan sijil** (`Urus jenis sijil, templat dan tetapan`)

- **Corak nombor siri**: lalai `{TYPE}-{YYYY}-{SEQ:6}` → `ENR-2026-000001`. Token ialah `{TYPE}` (kod jenis), `{YYYY}` dan `{YY}` (tahun pengeluaran, dalam zon waktu institusi) dan `{SEQ:n}` (nombor urutan n digit). Tepat satu `{SEQ:n}` diwajibkan, dan hanya teks biasa boleh mengikutinya. Nombor urutan dikira secara berasingan bagi setiap awalan yang berbeza: `{TYPE}-{SEQ:6}` dikira mengikut jenis merentas tahun, `{YYYY}{SEQ:5}` mengikut tahun merentas jenis. Pengeluaran serentak tidak pernah bertembung (pembilang ditambah secara atomik dalam pangkalan data).
- **Pengesahan sah selama (hari)**: 0 bermaksud sentiasa. Selepas tempoh tersebut, halaman pengesahan menjawab "telah luput". Pengeluaran itu sendiri kekal dalam daftar.
- **Penandatangan mengikut bahasa**: nama yang dicetak di atas cop mohor ("Naib Canselor, Universiti Ninefruits"), satu medan bagi setiap bahasa yang disokong oleh institusi. Penandatangan dalam templat diutamakan.

## Pengeluaran

**Keluarkan sijil** pada skrin rekod pelajar: jenis (yang aktif), bahasa (bahasa institusi), tujuan, salinan (1 hingga 20). **Keluarkan sijil** menjana dan menyimpan PDF lalu kembali ke rekod pelajar; notis memaparkan nombor siri beserta pautan **PDF**.

Pengeluaran ditolak (skrin menyatakan sebabnya) apabila:

- sasaran jenis tidak sepadan (surat pengesahan pelajar bagi graduan, surat pengesahan tamat pengajian bagi pelajar semasa)
- jenis tidak aktif
- tiada templat bagi bahasa tersebut
- **sekatan sijil** sedang berkuat kuasa bagi pelajar (sekatan, [bab 20](20-registration.md)); tarik balik sekatan itu terlebih dahulu. Ia tetap menyekat walaupun kakitangan tidak dapat melihat sekatan tersebut.
- rekod pelajar berada di luar skop paparan, atau kakitangan tidak dibenarkan mengeluarkan sijil
- perkhidmatan PDF (Gotenberg) tidak menjawab: tiada apa-apa dikeluarkan dan "PDF tidak dapat dihasilkan" dipaparkan. Keluarkan semula kemudian.

Pengeluaran direkodkan dalam log aktiviti (`certificate.issued`: nombor matrik, jenis, bahasa, nombor siri, salinan; tujuan sebagai sebab).

## Sijil dikeluarkan

**Sijil > Sijil dikeluarkan**: tarikh pengeluaran, nombor siri, jenis dan bahasa, nombor matrik, nama, tujuan, salinan, status, kakitangan, serta pautan **PDF** dan **Halaman pengesahan** (tab baharu). Tapis mengikut jenis dan status; cari mengikut nombor siri, nombor matrik atau nama. Skop paparan adalah sama seperti bagi rekod pelajar.

- **PDF**: membuka fail yang disimpan. Ia tidak dijana semula, jadi ia tepat seperti yang dikeluarkan.
- **Halaman pengesahan**: membuka halaman awam.
- **Jana semula** (menu baris): menjana PDF baharu daripada data semasa, cth. selepas membetulkan templat, dan menggantikan fail. Nombor siri dan kod pengesahan kekal; checksum berubah. Peristiwa audit `certificate.rerendered`. Sama seperti arahan `certificate_render`. Sijil yang dibatalkan tidak dijana semula.
- **Batalkan** (menu baris): sebab diwajibkan. Baris dan fail kekal, status menjadi dibatalkan, dan halaman pengesahan menjawab "dibatalkan". Peristiwa audit `certificate.revoked`. Sijil yang dibatalkan tidak dipulihkan; sijil baharu dikeluarkan.

Baris daftar tidak boleh disunting atau dipadam pada skrin (baris membuka butiran baca sahaja beserta checksum).

## Pengesahan

- URL pengesahan (`{institution address}/verify/{code}/`) dan kod QR dicetak di bahagian bawah sijil. Kod tersebut ialah rentetan rawak 20 aksara (huruf besar dan digit); huruf besar atau kecil tidak penting. Alamat diambil daripada pemboleh ubah persekitaran `APP_URL`.
- Halaman dibuka tanpa log masuk dan dihadkan kepada 30 permintaan seminit bagi setiap alamat (IP; HTTP 429 jika melebihi). Enjin carian diminta untuk tidak mengindeksnya (`noindex`). Ia menunjukkan sama ada sijil telah dikeluarkan, jenisnya, nombor siri, tarikh pengeluaran, serta nama dan nombor matrik yang disamarkan. Kod yang dibatalkan, telah luput dan tidak dikenali masing-masing mendapat jawapan yang berbeza. Medan kod pada halaman tersebut juga menyemak kod (`/verify/?code=...`).
- Untuk menyemak fail PDF yang diserahkan itu sendiri, bandingkan checksum (SHA-256) dalam butiran daftar dengan hash fail tersebut. Arahan `uv run manage.py certificate_verify {code}` juga menyemak kod ([arahan](../operations/commands.md)).
- Sistem lain mendapat semakan yang sama dengan butiran yang sama dalam bentuk JSON: `GET /api/v1/certificates/verify/<verification code>/` (tanpa log masuk, 30 permintaan seminit bagi setiap alamat, [panduan integrasi LMS](../../../lms-integration-guide.md)).

## Portal pelajar

**Sijil** (menu pelajar dan alumni): sijil yang dikeluarkan pada rekod pelajar itu sendiri (tarikh pengeluaran, jenis dan bahasa, nombor siri, status) beserta PDF. Sijil yang dibatalkan disenaraikan bersama statusnya tetapi tanpa pautan PDF, dan pelajar tidak boleh memuat turun PDF sijil yang dibatalkan (kakitangan yang mengeluarkan boleh membukanya untuk menyemak rekod). Fail pelajar lain tidak boleh dibuka (dikuatkuasakan dalam aplikasi dan pangkalan data). Alamat PDF ialah `/certificates/{issue id}/download/`.

## Soalan lazim

- **Nama dieja dengan salah.** Betulkan varian nama individu tersebut (dalam bahasa berkenaan) dan **Jana semula**. Jika sijil sudah diserahkan, batalkannya dan keluarkan sijil baharu.
- **Saya telah mengubah templat; bagaimana dengan sijil yang sudah dikeluarkan?** Ia tidak berubah. **Jana semula** jika perlu (banyak sekali gus dengan arahan `certificate_render`).
- **Satu nombor siri telah dilangkau.** Apabila ralat berlaku semasa pengeluaran (cth. perkhidmatan PDF tidak berfungsi), nombor tersebut telah digunakan dan tiada baris daftar yang tinggal. Nombor dijamin unik, bukan berturutan.
- **Kod QR menghala ke `localhost`.** Tetapkan `APP_URL` pada pelayan pengeluaran kepada alamat institusi, kemudian **Jana semula** sijil yang terjejas.

## Skrin dalam pemasangan ini

Skrin dan fungsinya sama seperti sistem asal (Filament, Livewire); cara mengendalikannya sedikit berbeza.

- **Keluarkan sijil** membuka halaman borang dan bukannya dialog. Sistem asal membuka PDF dalam tab baharu selepas pengeluaran; di sini skrin rekod pelajar dipaparkan semula dan pautan **PDF** dalam notis membukanya.
- Dalam daftar, **PDF** dan **Halaman pengesahan** ialah pautan di hujung baris; **Jana semula** (halaman pengesahan tindakan) dan **Batalkan** (halaman sebab) berada dalam menu baris. Jana semula hanya berfungsi bagi sijil yang tidak dibatalkan.
- Templat disunting di bahagian bawah skrin suntingan jenis. Dua templat bagi bahasa yang sama ditolak. Dengan `Lihat data rujukan` sahaja, jenis dan templat adalah baca sahaja.
- Apabila perkhidmatan PDF gagal semasa pengeluaran, tiada apa-apa dikeluarkan (dalam sistem asal, baris daftar boleh tertinggal tanpa PDF).
- Kebenaran pengeluaran hanya dikira apabila diberikan secara global (sistem asal membenarkan pemberian berskop pada skrin, lalu pangkalan data menolak baris tersebut dengan ralat).
- Dalam demo (`setup_demo`), `certificate-officer@demo.test` memaparkan daftar dan `student@demo.test` memaparkan **Sijil** portal.

[Kandungan manual pentadbir](README.md)
