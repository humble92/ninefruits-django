# 24. Peperiksaan

Menu: **Peperiksaan > Sesi peperiksaan**, **Keputusan peperiksaan**, **Pembetulan keputusan**, **Jenis peperiksaan**. Pelajar mendaftar dan melihat keputusan mereka dalam portal di bawah **Peperiksaan**.

| Kebenaran | Apa yang dibenarkan |
|---|---|
| `Daftarkan pelajar, masukkan dan terbitkan keputusan, rekod keputusan luar` | Mendaftarkan, membatalkan dan menandakan pelajar tidak hadir, memasukkan keputusan, mengimport CSV, menerbitkan keputusan, memohon pembetulan, merekod dan mengalih keluar keputusan luar, melihat daftar keputusan (dalam skop paparan rekod pelajar) |
| `Urus jenis peperiksaan, bahagian dan sesi` | Mencipta dan menyunting jenis, bahagian dan sesi, menukar markah lulus sesuatu sesi, meluluskan dan menolak permohonan pembetulan |

Lalai peranan: Pegawai Pendaftar dan Pegawai Hal Ehwal Akademik mempunyai kedua-duanya. Skrin jenis dan sesi juga memerlukan `Lihat data rujukan` (termasuk dalam lalai peranan). Keputusan hanya boleh dilihat dalam skop paparan rekod pelajar, jadi berikan juga `Lihat rekod pelajar` (atau kebenaran mengurus).

## Perbezaan daripada sistem lama

- **Tiada lajur tetap bagi setiap jenis.** Sistem lama (YUSTIC) mempunyai empat lajur tatabahasa, menulis, mendengar dan membaca yang dikodkan secara tetap dalam `CET`, satu huruf P/N bagi setiap subjek untuk peperiksaan komprehensif (`SSCORE_ADD`), dan satu lagi jadual untuk peperiksaan komputer (`COMEXAM`). Sistem baharu mentakrifkan bahagian dan kaedah pemarkahan pada **jenis peperiksaan** dan mengendalikan setiap peperiksaan dengan struktur sesi, pendaftaran dan keputusan yang sama.
- **Keputusan lulus.** Dalam sistem lama, jumlah keempat-empat bahagian pada atau melebihi markah potong bermakna lulus, tanpa minimum bagi setiap bahagian. Sistem baharu memutuskan dengan markah lulus jenis (atau sesi) dan **minimum bagi setiap bahagian**, dan menyimpan keputusan tersebut pada rekod keputusan. Jenis lulus/gagal diputuskan oleh kakitangan.
- **Tempoh pendaftaran dan kapasiti.** Sistem lama tiada kedua-duanya. Sesuatu sesi mempunyai masa pembukaan dan penutupan pendaftaran serta kapasiti.
- **Penerbitan keputusan.** Dalam sistem lama, pelajar melihat keputusan sebaik sahaja ia dimasukkan, dan hanya bagi sesi terkini. Dalam sistem baharu, pelajar melihat keputusan selepas **Terbitkan keputusan** bagi sesi tersebut, dan keputusan setiap sesi disimpan. Sesi yang mempunyai keputusan tidak boleh dipadam.
- **Keputusan luar.** Sistem lama tiada tempat untuk merekod ujian luar seperti TOEFL atau TOPIK (kotak HSK pada helaian semakan bergraduat hanyalah label kosong). Keputusan luar direkodkan bersama fail bukti.
- **Pautan kepada syarat bergraduat.** Dalam sistem lama, seseorang membaca helaian semakan bergraduat dan membuat keputusan. Jenis syarat **Lulus peperiksaan** memasukkannya ke dalam kurikulum ([bab 17](17-courses-and-curriculum.md)).

## Jenis peperiksaan dan bahagian

**Jenis peperiksaan**: kod, nama (bagi setiap bahasa), kategori (Bahasa, Komprehensif, Tesis, Ujian luar), pemarkahan, markah maksimum, markah lulus, keputusan luar, aktif, susunan.

| Pemarkahan | Input | Keputusan |
|---|---|---|
| Markah | Markah bagi setiap bahagian (jumlah apabila tiada bahagian) | Jumlah ≥ markah lulus dan setiap bahagian ≥ minimumnya. Tanpa markah lulus, kakitangan memilih |
| Lulus/gagal | Lulus atau tidak | Kakitangan memilih |

**Bahagian** (tab **Bahagian** pada skrin suntingan jenis): kod (nama lajur CSV; huruf, digit, `-`, `_`), nama, markah maksimum, minimum untuk lulus (pilihan), susunan. Dengan bahagian, jumlah ialah hasil tambah markah bahagian. Markah yang sama dengan minimum bahagian dikira lulus bahagian itu; kurang satu mata sahaja menyebabkan pelajar gagal tanpa mengira jumlahnya.

Jenis yang disemai oleh profil universiti Korea (`setup_install --profile=korean-university`):

| Kod | Jenis | Keputusan | Catatan |
|---|---|---|---|
| `ENG_COMP` | Peperiksaan komprehensif bahasa Inggeris | Markah, lulus pada 60 | Mendengar, membaca, menulis, tatabahasa, 25 mata setiap satu |
| `COMP_EXAM` | Peperiksaan komprehensif komputer | Lulus/gagal | |
| `THESIS` | Tesis tamat pengajian | Lulus/gagal | |
| `TOPIK` | Ujian Kecekapan Bahasa Korea | Lulus/gagal, luar | Tahap dan nombor sijil direkodkan |

Menjalankan profil sekali lagi mengekalkan nilai yang telah diubah oleh pentadbir dan tidak mengembalikan bahagian yang telah mereka buang.

## Sesi

**Sesi peperiksaan**: jenis, tarikh (unik bagi setiap jenis), tempat, kapasiti, pendaftaran dibuka dan ditutup, markah lulus (kosong: nilai jenis). Tab **Pendaftar** pada skrin sesi menyenaraikan pendaftaran.

- **Daftarkan pelajar** (masukkan nombor matrik): kakitangan boleh mendaftarkan pelajar tanpa mengira tempoh pendaftaran, sehingga tarikh peperiksaan. Kapasiti terpakai. Tiada sesiapa boleh didaftarkan bagi sesi yang tarikhnya telah berlalu. Keputusan hanya dimasukkan bagi pelajar yang berdaftar; baris CSV bagi pelajar yang tidak berdaftar dilaporkan sebagai ralat dan dilangkau.
- Pelajar mendaftar dan membatalkan dalam portal semasa tempoh pendaftaran. Hanya pelajar yang sedang belajar dan tangguh pengajian boleh berbuat demikian. Mendaftar semula selepas membatalkan akan mengaktifkan semula pendaftaran yang sama.
- **Masukkan keputusan**: markah bagi setiap bahagian (atau jumlah), lulus atau tidak jika perlu, catatan. Sebelum penerbitan, memasukkan sekali lagi akan menulis gantinya (peristiwa audit `assessment.result_recorded`). **Selepas penerbitan ia dikunci** (lihat permohonan pembetulan di bawah).
- **Tidak hadir**: berdaftar tetapi tidak menduduki peperiksaan. Memasukkan keputusan mengembalikan pendaftaran kepada berdaftar.
- **Batalkan pendaftaran**: pendaftaran yang mempunyai keputusan tidak boleh dibatalkan. Sebab adalah pilihan.
- **Terbitkan keputusan**: mulai saat ini pelajar melihat keputusan sesi ini. Selepas penerbitan, keputusan tidak boleh disunting atau dipadam secara terus; ia berubah melalui **permohonan pembetulan** (keputusan 2026-10-23). Sama seperti arahan `assessment_publish_results`.
- **Markah lulus** sesi (mengatasi nilai jenis): digunakan apabila mesyuarat menurunkan markah potong kerana peperiksaan sukar. Ia boleh diubah **sebelum penerbitan**, dan apabila ia disimpan, setiap keputusan yang telah dimasukkan bagi sesi tersebut **dinilai semula** daripada markah yang disimpan (jumlah berbanding ambang baharu, minimum bahagian seperti yang ditetapkan pada jenis). Dengan **Sebab menukar markah lulus**, peristiwa audit `assessment.pass_score_changed` menyimpan ambang lama dan baharu bersama nombor matrik yang keputusannya berubah. Selepas disimpan, skrin memaparkan bilangan keputusan yang dinilai semula. **Selepas penerbitan** ia hanya boleh dibaca (permohonan pembetulan sahaja). Minimum bagi setiap bahagian tidak boleh diubah pada sesi (tetapan jenis).
- **Import keputusan (CSV)**: format di bawah. Baris bagi pelajar yang tidak berdaftar dilangkau sebagai ralat. Sama seperti arahan `assessment_import_results`.

Format CSV (baris pengepala, UTF-8, sehingga 5 MB):

| Lajur | Kandungan |
|---|---|
| `student_number` | Nombor matrik (wajib) |
| Kod bahagian (`LISTENING`, …) | Markah bahagian. Tidak sensitif huruf besar/kecil |
| `total` | Jumlah bagi jenis tanpa bahagian |
| `passed` | `Y`/`N`. Wajib bagi jenis lulus/gagal atau jenis tanpa markah lulus |
| `absent` | `Y` menandakan pelajar tidak hadir |
| `note` | Catatan |

Baris ralat dilangkau dan dilaporkan bersama nombor barisnya dalam mesej hasil (skrin, 10 yang pertama) atau output (arahan). Teks ralat adalah dalam bahasa Inggeris, sama seperti output arahan.

## Pembetulan keputusan

Prosedur untuk mengubah keputusan sesi yang telah diterbitkan. Ia berfungsi seperti pindaan gred.

1. **Mohon pembetulan** pada tab **Pendaftar** sesi: markah baharu (atau lulus atau tidak) dan sebab. Satu permohonan menunggu bagi setiap keputusan. Peristiwa audit `assessment.correction_requested`.
2. Di bawah **Peperiksaan > Pembetulan keputusan**, pemegang kebenaran `Urus jenis peperiksaan, bahagian dan sesi` mengklik **Luluskan** (catatan pilihan) atau **Tolak** (catatan diwajibkan). **Tiada sesiapa boleh memutuskan permohonannya sendiri.**
3. Setelah diluluskan, keputusan berubah kepada nilai baharu serta-merta (keputusan lulus dibuat semula daripada markah baharu) dan pelajar dapat melihatnya. Peristiwa audit `assessment.correction_approved`, `assessment.result_corrected`. Pemohon boleh membatalkan permohonan sehingga ia diputuskan.

Senarai memaparkan permohonan yang menunggu secara lalai (penapis status **Semua** untuk setiap permohonan), dengan nilai semasa dan nilai dicadangkan bersebelahan. Menu memaparkan bilangan permohonan yang menunggu.

## Daftar keputusan

**Keputusan peperiksaan**: setiap keputusan (sesi dan luar). Tapis mengikut jenis, sumber dan lulus; cari mengikut nombor matrik atau nama. Skop paparan adalah sama seperti bagi rekod pelajar.

- **Rekod keputusan luar** (di atas senarai): nombor matrik, jenis (hanya jenis yang membenarkan keputusan luar), tarikh diduduki (bukan pada masa hadapan), jumlah, tahap, lulus atau tidak, nombor sijil, fail bukti (PDF, JPG, PNG, 5 MB), catatan. Peristiwa audit `assessment.external_recorded`.
- **Bukti**: membuka fail. Pelajar boleh membuka fail mereka sendiri.
- **Alih keluar** (baris): sebab diwajibkan, peristiwa audit `assessment.result_removed`. Untuk memadam dan merekod semula keputusan luar yang dimasukkan dengan salah atau keputusan sebelum penerbitan. Fail bukti turut dipadam. Keputusan sesi yang telah diterbitkan tidak boleh dialih keluar (permohonan pembetulan).

## Syarat bergraduat

Dalam **Kurikulum > Syarat bergraduat**, pilih jenis syarat **Lulus peperiksaan** dan pilih **Jenis peperiksaan**. Pelajar memenuhinya dengan sekurang-kurangnya satu keputusan lulus (sesi atau luar) bagi jenis tersebut. Bahagian atas halaman **Peperiksaan** portal memaparkan jenis yang diwajibkan oleh kurikulum pelajar dan sama ada ia telah lulus. Semakan bergraduat ([bab 26](26-graduation.md)) membaca syarat ini. Jenis yang digunakan oleh sesuatu syarat tidak boleh dipadam (jadikannya tidak aktif).

## Portal pelajar

**Peperiksaan**: syarat kurikulum dan sama ada ia telah lulus, sesi yang dibuka untuk pendaftaran (daftar, batal), pendaftaran saya, keputusan saya (sesi yang diterbitkan dan keputusan luar, markah bahagian, bukti).

## Skrin dalam pemasangan ini

Skrin dan cirinya adalah sama seperti sistem asal (Filament, Livewire); cara mengendalikannya sedikit berbeza.

- Menu baris senarai **Sesi peperiksaan**: **Terbitkan keputusan** (halaman pengesahan), **Import keputusan (CSV)** (halaman fail). Butang di bahagian atas skrin sesi: **Daftarkan pelajar** (sehingga tarikh peperiksaan), **Import keputusan (CSV)**, **Terbitkan keputusan**. Penapis: jenis, keputusan diterbitkan.
- Tab **Pendaftar** pada skrin sesi ditapis dengan mengklik sesuatu status (Semua, Berdaftar, Dibatalkan, Tidak hadir). Pautan baris **Masukkan keputusan**, **Mohon pembetulan**, **Tidak hadir** dan **Batalkan pendaftaran** membuka halaman kemasukan. Halaman keputusan mempunyai medan markah bagi setiap bahagian jenis tersebut dan, bagi jenis yang diputuskan daripada markah, menerangkan peraturannya.
- **Rekod keputusan luar** di atas senarai **Keputusan peperiksaan**, **Alih keluar** dalam menu baris. Pautan dalam lajur bukti membuka fail dalam tetingkap baharu.
- Menu baris **Pembetulan keputusan**: **Luluskan**, **Tolak**, **Batalkan permohonan** (permohonan sendiri).
- Alamat bukti: `/assessment-results/{result ID}/evidence/` (dimuat turun selepas semakan kebenaran). Alamat portal: `/portal/assessments/`.
- Arahan: `uv run manage.py assessment_import_results {kind code} {date} {CSV} --actor=... [--dry-run]`, `uv run manage.py assessment_publish_results {kind code} {date} --actor=...` ([arahan operasi](../operations/commands.md)).

## Soalan lazim

- **Saya perlu mendaftarkan pelajar di luar tempoh pendaftaran.** Kakitangan mendaftarkan mereka dengan **Daftarkan pelajar** pada skrin sesi.
- **Saya mahu menukar markah lulus bagi sesi ini sahaja.** Sebelum penerbitan, masukkan markah lulus sesi tersebut bersama sebab dan simpan. Keputusan yang telah dimasukkan dinilai serta-merta berdasarkan ambang baharu.
- **Saya tersalah memasukkan markah.** Sebelum penerbitan, **Masukkan keputusan** sekali lagi untuk menulis gantinya. Selepas penerbitan, buat **permohonan pembetulan** dan minta kakitangan lain meluluskannya.
- **Statistik pelajar tidak hadir.** Tapis tab **Pendaftar** mengikut status **Tidak hadir**.

[Kandungan manual pentadbir](README.md)
