# 21. Gred

Menu: **Gred > Kemajuan gred**, **Permohonan kaedah penilaian**, **Pindaan gred**, **Rekod semester**, **Tetapan > Dasar penggredan**. Pensyarah menggunakan **Pengajaran saya > Masukkan gred** dalam portal.

| Kebenaran | Apa yang dibenarkan |
|---|---|
| `Lihat gred, kemajuan gred dan rekod semester` | Melihat kemajuan gred, rekod semester dan laporan gred pelajar |
| `Muktamadkan dan kembalikan gred, masukkan gred bagi pihak pensyarah, tutup semester` | Memuktamadkan atau mengembalikan gred seksyen, memasukkan gred bagi pihak pensyarah (tanpa mengira tempoh), menghantar gred di luar had gred sebagai pengecualian, menutup semester, mengira semula. Apabila ditetapkan dengan skop unit organisasi, hanya seksyen yang ditawarkan oleh unit tersebut |
| `Dimaklumkan apabila kakitangan menghantar gred di luar had gred (ketua jabatan, pejabat akademik)` | Menerima pemberitahuan penghantaran sebagai pengecualian. Ditetapkan dengan skop unit organisasi kepada ketua jabatan dan ketua pejabat akademik |
| `Mohon pindaan gred muktamad` | Memohon pindaan bagi seksyen yang tidak diajar sendiri (cth. membatalkan gred kerana salah laku akademik) |
| `Luluskan atau tolak pindaan gred (bukan permohonan sendiri)` | Memutuskan permohonan pindaan gred |
| `Urus dasar PNG, ulang kursus, kedudukan akademik dan Senarai Dekan` | Tetapan dasar penggredan |

Pensyarah memasukkan gred dan memohon pindaan bagi seksyen mereka sendiri tanpa sebarang kebenaran. Lalai peranan: Pegawai Pendaftar mempunyai kebenaran melihat, memuktamadkan, meluluskan dan semakan pengecualian; Pegawai Hal Ehwal Akademik mempunyai kebenaran melihat, permohonan pindaan dan dasar; Pegawai Sijil dan Pembantu Jabatan mempunyai kebenaran melihat. Permohonan kaedah penilaian diputuskan dengan kebenaran `Rancang seksyen (pensyarah, waktu, bilik)`.

## Perbezaan daripada sistem lama

- Dalam sistem lama (YUSTIC), gred yang disimpan oleh pensyarah serta-merta menjadi muktamad, dan pejabat akademik menyuntingnya secara terus pada skrin. Tiada sebab dan tiada langkah kelulusan, malah suntingan oleh sesetengah akaun tidak muncul dalam rekod sandaran. Sistem baharu mempunyai peringkat **masukkan → hantar → muktamadkan**, dan gred muktamad hanya berubah apabila **orang lain meluluskan permohonan pindaan**. Kedua-dua aplikasi dan pangkalan data (pencetus) menguatkuasakan perkara ini.
- Dalam sistem lama, pensyarah boleh menyimpan gred bagi seksyen yang tidak diajarnya dengan memanipulasi permintaan. Sistem baharu menyemak pensyarah yang ditetapkan dan skop kebenaran pada pelayan dan dalam pangkalan data.
- PNG, amaran akademik dan Senarai Dekan tidak dikira secara langsung pada setiap skrin; ia disimpan sebagai **rekod semester**. Semasa penutupan semester, ia menjadi rekod rasmi semester tersebut.
- Ulang kursus mengeluarkan gred terdahulu daripada PNGK hanya **selepas gred baharu dimuktamadkan** (sistem lama mengeluarkannya semasa pendaftaran dan tidak membatalkannya apabila seksyen dibatalkan).
- Sistem lama hanya menyahdayakan menu gred; gred masih boleh dilihat melalui alamat. Sistem baharu menguatkuasakan sekatan paparan gred pada pelayan.

## Susunan dalam satu semester

1. **Tempoh urusan** ([bab 10](10-terms.md)): tempoh **Kemasukan gred** bagi setiap sesi. Pensyarah memasukkan dan menghantar gred hanya dalam tempoh ini.
2. Pensyarah memasukkan dan menghantar gred. `uv run manage.py grades_remind_missing {term}` menghantar e-mel peringatan kepada pensyarah yang belum menghantar.
3. Pada **Kemajuan gred**, muktamadkan setiap seksyen atau kembalikannya kepada pensyarah.
4. Apabila setiap seksyen telah dimuktamadkan, **Rekod semester > Tutup semester**. Rekod semester, kedudukan akademik dan Senarai Dekan ditentukan dan semester beralih kepada **Gred ditutup**.
5. Gred yang dipinda selepas itu melalui **Pindaan gred**.

## Skala gred dan kaedah penilaian

**Skala gred ditetapkan semasa pemasangan dan tidak boleh diubah** (keputusan 2026-10-23), kerana setiap gred dan PNG adalah berdasarkan skala tersebut. Tetapkannya dengan `uv run manage.py setup_install --grade-scale=4.5|4.3`; jika tidak, skala profil pertama digunakan (universiti Korea 4.5, YUST lama 4.3). Tanda **Lalai** di bawah Data rujukan > Skala gred tidak boleh dipindahkan dan skala lalai tidak boleh dipadam. **Julat markah** (% bawah dan atas) dan nilai gred bagi setiap gred disunting pada skrin tersebut ([bab 11](11-course-categories-and-grade-scales.md)).

Setiap seksyen mempunyai **kaedah penilaian**. Lalainya ialah **Penilaian mutlak**.

| Kaedah penilaian | Pensyarah memasukkan | Disimpan | Syarat penghantaran |
|---|---|---|---|
| Penilaian mutlak (lalai) | **Markah (0–100)** bagi setiap pelajar. Gred ditentukan daripada julat markah dan tidak boleh dipilih (hanya gred tanpa markah, cth. I, dipilih secara terus) | Markah (asal), gred, nilai gred | Gred bagi setiap pelajar |
| Penilaian relatif | **Gred** bagi setiap pelajar. Markah tidak dimasukkan (ditolak jika dimasukkan) | Gred, nilai gred | Gred bagi setiap pelajar + **had gred** dipatuhi |
| Kursus lulus/gagal | P/NP tanpa mengira kaedah penilaian | Gred | Gred bagi setiap pelajar |

- Pensyarah yang mahukan penilaian relatif mengklik **Mohon Penilaian relatif** (dengan sebab) pada skrin kemasukan gred. Pemegang kebenaran `Rancang seksyen (pensyarah, waktu, bilik)` bagi unit penawar (pembantu jabatan, hal ehwal akademik) meluluskan atau menolaknya (catatan diwajibkan) di bawah **Gred > Permohonan kaedah penilaian**, dan pensyarah dimaklumkan melalui e-mel. Setelah diluluskan, draf gred yang dimasukkan dengan kaedah lama dikosongkan. Setelah gred **dihantar**, permohonan mahupun perubahan tidak lagi boleh dibuat. Kakitangan juga boleh menukar kaedah pada skrin seksyen, tetapi hanya sehingga gred dimasukkan.
- Gred tertinggi bagi ulang kursus: dalam penilaian mutlak, markah yang akan memberikan gred lebih tinggi daripada had **diturunkan kepada gred had** (markah kekal). Dalam penilaian relatif, gred melebihi had tidak boleh dipilih.

## Had gred (penilaian relatif)

**Tetapan > Dasar penggredan > Penilaian relatif**: had bagi setiap kumpulan gred (lalai kumpulan A 30%, kumpulan B 40%), toleransi melebihi had (lalai 1 mata peratusan), bilangan minimum pelajar bergred untuk semakan (lalai 10).

- Kumpulan gred adalah mengikut huruf: A+, A0 dan A- membentuk kumpulan A; B+, B0 dan B- kumpulan B. Kumpulan tanpa had (C, D, F) tidak terhad.
- Penyebutnya ialah bilangan pelajar dalam seksyen yang mempunyai gred yang dikira dalam PNG. Pelajar yang tarik diri dan P/NP/I dikecualikan.
- Seksyen di bawah bilangan minimum pelajar tidak disemak (30% A daripada 7 pelajar tidak mungkin dipenuhi).
- Pensyarah melihat taburan semasa berbanding had dengan **Semak had gred** pada skrin kemasukan gred, dan **tidak boleh menghantar** melebihi had.
- Kakitangan yang mempunyai kebenaran pengurusan gred boleh menghantar melebihi had, tetapi sebagai **penghantaran pengecualian**: sebab diwajibkan, taburan dan sebab direkodkan dalam log aktiviti, pemegang kebenaran `Dimaklumkan apabila kakitangan menghantar gred di luar had gred (ketua jabatan, pejabat akademik)` (ketua jabatan, ketua pejabat akademik, ditetapkan dengan skop unit organisasi) menerima e-mel, dan seksyen ditandakan **Dihantar sebagai pengecualian**. **Kemajuan gred** boleh ditapis untuk memaparkan penghantaran pengecualian sahaja.

## Kemasukan gred (pensyarah)

Dalam portal di bawah **Pengajaran saya**, buka **Masukkan gred** bagi seksyen. Bahagian atas skrin memaparkan kaedah penilaian seksyen, arahan kemasukan dan permohonan kaedah penilaian.

- Penilaian mutlak: gred muncul sebaik sahaja markah dimasukkan.
- Penilaian relatif: hanya gred dipilih. Tiada lajur markah. Semak had dengan **Semak had gred** dan hantar.
- Senarai gred mengikut asas penggredan kursus. Kursus bergred memaparkan gred huruf, kursus lulus/gagal memaparkan P/NP ([bab 11](11-course-categories-and-grade-scales.md)).
- **Simpan draf** boleh dilakukan pada bila-bila masa. Pelajar tidak melihat draf gred.
- **Hantar gred** memerlukan gred bagi setiap pelajar. Selepas penghantaran, pensyarah tidak lagi boleh mengubahnya. Bagi gred yang salah, minta pejabat akademik mengembalikan gred sebelum dimuktamadkan, atau mohon pindaan selepasnya.
- Pelajar yang tarik diri dipaparkan sebagai W dan tidak mendapat gred.

## Memuktamadkan dan mengembalikan (pejabat akademik)

**Kemajuan gred**: seksyen bagi sesuatu semester beserta bilangan yang belum dihantar, dihantar dan muktamad. Penapis **Sedia dimuktamadkan** hanya memaparkan seksyen yang gred setiap pelajarnya telah dihantar.

- **Muktamadkan**: memuktamadkan gred yang dihantar. Pendaftaran menjadi **Selesai** dan pelajar melihat gred mereka. Rekod semester pelajar dikira semula. Beberapa seksyen boleh dipilih dan dimuktamadkan dengan **Muktamadkan yang dipilih**. Seksyen yang mempunyai pelajar yang belum dihantar grednya dilangkau.
- **Kembalikan kepada pensyarah**: membatalkan penghantaran dengan sebab. Gred kembali kepada draf dan pensyarah menerima e-mel.
- **Gred**: membuka skrin kemasukan gred. Pejabat akademik boleh memasukkan atau mengubah gred sebelum dimuktamadkan tanpa mengira tempoh. Apabila kakitangan mengubah gred yang telah **dihantar** oleh pensyarah, nilai lama dan baharu direkodkan dalam peristiwa audit `grades.submitted_changed`.

## Pindaan gred

Satu-satunya cara untuk mengubah gred muktamad.

1. Permohonan: pensyarah mengklik **Mohon pindaan** bagi pelajar pada skrin kemasukan gred (dengan sebab; markah baharu dalam penilaian mutlak, gred baharu dalam penilaian relatif). Had ulang kursus juga terpakai bagi pindaan. Bagi seksyen yang tidak diajarnya, kakitangan yang mempunyai kebenaran `Mohon pindaan gred muktamad` memohonnya pada skrin yang sama. Hanya satu permohonan terbuka bagi setiap gred.
2. Keputusan: di bawah **Gred > Pindaan gred** (lalai: senarai menunggu; menu memaparkan bilangan yang menunggu), klik **Luluskan** atau **Tolak** (catatan diwajibkan). Pemohon tidak boleh memutuskan permohonannya sendiri (turut dikuatkuasakan oleh kekangan pangkalan data).
3. Setelah diluluskan, gred (markah dan gred dalam penilaian mutlak) berubah serta-merta, dan rekod semester pelajar serta PNGK semester berikutnya dikira semula. Kedudukan akademik dan Senarai Dekan mengekalkan nilai yang ditentukan semasa penutupan semester.

Pemohon boleh **Batalkan permohonan** semasa ia masih menunggu. Setiap permohonan dan keputusan direkodkan dalam log aktiviti bersama sebabnya.

## Pengiraan PNG

| Item | Peraturan |
|---|---|
| Kredit diambil | Setiap kursus yang dimuktamadkan (termasuk F, P, NP, I) |
| Kredit diperoleh | Gred lulus (tidak termasuk F, NP, I) |
| Kredit PNG | Gred yang dikira dalam PNG. F dikira dengan 0 mata; P/NP/I dikecualikan |
| PNG | Jumlah (nilai gred × kredit) ÷ kredit PNG. Semester yang hanya mempunyai kursus lulus/gagal tiada PNG |
| Tempat perpuluhan | Tempat perpuluhan dan pembundaran (bundar separuh ke atas, potong) daripada dasar. Aritmetik integer, jadi tiada ralat pada sempadan (cth. 3.4375 → 3.438) |
| PNG semester | Setiap gred semester tersebut (gred terdahulu yang digantikan oleh ulang kursus masih dikira dalam PNG semesternya sendiri) |
| PNGK | Kursus yang diulang dikira sekali sahaja, mengikut dasar: **Percubaan terkini** (lalai; yang terkini walaupun lebih buruk) atau **Percubaan terbaik**. Gred yang digantikan juga dikecualikan daripada kredit kumulatif dan dipaparkan pada skrin gred sebagai "digantikan oleh ulang kursus dalam PNGK" |

Hubungan ulang kursus ditetapkan semasa pendaftaran ([bab 20](20-registration.md)): mengambil kursus yang sama atau kursus setara sekali lagi memautkannya kepada pendaftaran terdahulu.

## Kedudukan akademik dan Senarai Dekan (penutupan semester)

| Dasar | Lalai | Profil YUST lama |
|---|---|---|
| Ambang amaran | PNG semester di bawah 1.75 | Di bawah 1.3 |
| Nilai semester biasa sahaja | Ya | Ya |
| Amaran untuk semakan pemberhentian | 0 (mati) | 4 |
| Kira amaran berturut-turut sahaja | Tidak (jumlah keseluruhan) | Tidak |
| PNG minimum Senarai Dekan, kredit PNG minimum | 4.0, 15 kredit | 0, 0 (sistem lama hanya mengambil N teratas) |
| Tiada Senarai Dekan jika gagal mana-mana kursus | Ya | Tidak |
| Tempat perpuluhan PNG | 2, bundar separuh ke atas | 3, bundar separuh ke atas |
| Skala gred (ditetapkan semasa pemasangan) | 4.5 (KR45) | 4.3 (YUST43) |
| Had gred (penilaian relatif) | A 30%, B 40%, toleransi 1 mata peratusan, disemak mulai 10 pelajar | Sama |

- **Amaran akademik**: PNG semester **di bawah** ambang. Semester yang hanya mempunyai kursus lulus/gagal tidak memberikan amaran.
- **Semakan pemberhentian**: ditandakan apabila bilangan amaran mencapai ambang. Pemberhentian itu sendiri ialah perubahan status ([bab 13](13-status-changes-and-advisors.md)).
- Apabila hanya semester biasa dinilai, semester pendek (musim panas dan musim sejuk) tiada kedudukan akademik dan tidak memutuskan rangkaian amaran berturut-turut.
- **Senarai Dekan**: pelajar yang memenuhi kriteria disusun mengikut kedudukan bagi setiap program berdasarkan PNG semester (markah seri berkongsi kedudukan; kedudukan seterusnya dilangkau).
- **Kedudukan akademik** pada rekod pelajar berubah kepada hasil terkini. Kriteria "kedudukan akademik" dalam tempoh urusan dan kelayakan seksyen menggunakan nilai ini.

Pada skrin **Rekod semester**, tapis mengikut semester, kedudukan akademik, Senarai Dekan dan program untuk melihat senarai pelajar yang menerima amaran akademik dan Senarai Dekan (laporan amaran dan Senarai Dekan sistem lama). Jalankan **Tutup semester** terlebih dahulu dengan **Pratonton sahaja** (lalai) untuk melihat seksyen yang belum muktamad, kemudian matikannya dan jalankan sekali lagi. **Kira semula** menggunakan dasar yang telah diubah pada rekod semester lepas (sebab diwajibkan).

## Skrin pelajar dan laporan gred

Apabila kakitangan membuka laporan gred pelajar, ia direkodkan dalam peristiwa audit `transcript.viewed` (bersama nombor matrik).

- **Gred** portal: gred muktamad bagi setiap semester (tarik diri sebagai W), PNG semester dan kredit diperoleh, PNGK, kedudukan akademik, Senarai Dekan. Alumni juga boleh melihatnya. Gred yang belum muktamad tidak dipaparkan.
- **Cetak**, **PDF**: laporan gred tidak rasmi untuk semakan. PDF dihasilkan oleh Gotenberg. Transkrip rasmi dikeluarkan sebagai sijil ([bab 23](23-certificates.md)). Kakitangan membuka laporan gred pelajar dengan **Laporan gred** pada skrin rekod pelajar atau dalam Rekod semester (kebenaran `Lihat gred, kemajuan gred dan rekod semester`).
- Pelajar yang mempunyai **sekatan** dengan **Menyekat paparan gred** dihidupkan tidak dapat melihat skrin gred atau laporan gred ([bab 20](20-registration.md)).
- Semasa tempoh penilaian kursus, gred semester tersebut disembunyikan bagi pelajar yang belum melengkapkan penilaian kursus semester itu (satu tetapan, [bab 22](22-course-evaluation.md)).

## Dasar penggredan

**Tetapan > Dasar penggredan** (kebenaran `Urus dasar PNG, ulang kursus, kedudukan akademik dan Senarai Dekan`). Mengubah item dalam jadual di atas. Dasar yang diubah terpakai mulai pengiraan seterusnya. Untuk menggunakannya pada rekod semester lepas, **Kira semula**. Kedudukan akademik dan Senarai Dekan ditentukan semasa penutupan semester, jadi ia tidak digunakan semula pada semester yang telah ditutup.

## Skrin dalam pemasangan ini

Skrin dan fungsinya sama seperti sistem asal (Filament, Livewire); cara mengendalikannya sedikit berbeza.

- Menu baris **Kemajuan gred**: **Gred** (skrin kemasukan gred portal), **Muktamadkan** (skrin pengesahan), **Kembalikan kepada pensyarah** (skrin sebab). Untuk memuktamadkan beberapa seksyen, pilih seksyen tersebut dalam senarai dan pilih **Muktamadkan yang dipilih** dalam senarai tindakan. Penapis: semester (lalai: semester yang sedang berjalan, **Semua** untuk setiap semester), unit penawar, dihantar sebagai pengecualian, sedia dimuktamadkan.
- **Luluskan** dan **Tolak** dalam menu baris **Pindaan gred** dan **Permohonan kaedah penilaian** membuka skrin untuk catatan. Senarai lalai memaparkan permohonan yang belum diputuskan, dan menu memaparkan bilangan permohonan yang belum diputuskan.
- **Tutup semester** di atas senarai **Rekod semester**: semester, **Pratonton sahaja** (hidup secara lalai), sebab. Pratonton memaparkan dalam mesej sama ada semester boleh ditutup dan seksyen yang belum muktamad (sehingga 30). Penutupan yang dimulakan dijalankan sebagai tugas dalam baris gilir (Celery) yang setiap satunya mengandungi 100 pelajar; penutupan yang sedang berjalan memaparkan kemajuannya di atas senarai rekod semester. Apabila selesai, semester beralih kepada **Gred ditutup** dan kakitangan yang memulakannya menerima e-mel. Jika sesuatu tugas gagal, penutupan tidak selesai dan semester kekal seperti sedia ada; betulkan puncanya dan tutup sekali lagi (ia memberikan hasil yang sama). Daripada baris arahan: `uv run manage.py term_close {term} --dry-run`, `uv run manage.py term_close {term} --reason=...` ([arahan](../operations/commands.md)).
- Dalam **Dasar penggredan**, tulis had gred sebagai huruf dan peratusan yang dipisahkan dengan koma, cth. `A=30, B=40`. Kosong bermaksud tiada had.
- Kemasukan gred portal: dalam penilaian mutlak, gred muncul di sebelah markah sejurus selepas markah ditaip. **Simpan draf**, **Semak had gred** dan **Hantar gred** berada di bahagian bawah skrin; apabila penyimpanan gagal (cth. markah di luar julat), nilai yang dimasukkan dipaparkan semula bersama ralat. **Mohon pindaan** pada baris pelajar membuka medan permohonan di bawah jadual.
- Alamat laporan gred bagi kakitangan: `/student-records/{student record id}/transcript/` (butang **Laporan gred** pada skrin rekod pelajar, **Laporan gred** pada baris rekod semester). Tambah `?format=pdf` untuk PDF.
- Bagi seksyen yang dipautkan kepada LMS, skrin kemasukan gred boleh memuatkan markah LMS sebagai draf ([bab 28](28-lms-integration.md)). Gred bagi semester yang penilaian kursusnya dibuka dan belum dilengkapkan disembunyikan dengan notis dan pautan ke **Penilaian kursus** ([bab 22](22-course-evaluation.md)).

[Kandungan manual pentadbir](README.md)
