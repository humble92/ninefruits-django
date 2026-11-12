# 25. Bilik Darjah Pensyarah dan Kehadiran

Menu: pensyarah menggunakan **Pengajaran saya > Senarai pelajar dan kehadiran** dalam portal (`/portal/sections/{section ID}/attendance/`), pelajar menggunakan **Kehadiran** dalam portal (`/portal/attendance/`). Kakitangan menggunakan tab **Sesi kelas** pada skrin **Kurikulum dan seksyen > Seksyen > Tukar** dalam panel pentadbiran.

| Siapa | Apa yang boleh dilakukan |
|---|---|
| Pensyarah yang ditetapkan | Senarai pelajar (dengan foto) dan CSV, PDF borang kehadiran, menjana, menambah dan membatalkan sesi kelas, memasukkan kehadiran |
| Kakitangan dengan `Rancang seksyen (pensyarah, waktu, bilik)` (dalam skop) | Sama seperti pensyarah + sesi kelas dalam panel pentadbiran |
| Kakitangan dengan `Lihat seksyen` (dalam skop) | Senarai pelajar, borang kehadiran, melihat kehadiran |
| Pelajar | Kehadiran mereka sendiri |

Ciri bilik darjah seperti pengumuman, tugasan dan bahan diserahkan kepada LMS (pelan pemindahan bahagian 12).

## Perbezaan daripada sistem lama

- **Sistem lama (YUSTIC) tidak merekod kehadiran.** "Borang kehadiran"nya ialah PDF yang mencetak kotak kosong (27 hingga 34 kotak, berbeza mengikut salinan) di sebelah senarai pelajar, tanpa tarikh dan tanpa jumlah. Sistem baharu mencipta **sesi kelas** daripada waktu kelas, merekod hadir, lewat, tidak hadir atau dikecualikan bagi setiap sesi kelas, dan mencetak rekod serta jumlah pada PDF borang kehadiran.
- **Senarai pelajar.** Skrin pensyarah sistem lama hanya memaparkan nombor matrik dan nama (serta mendedahkan nombor pendaftaran penduduk dan alamat dalam tetingkap timbul) dan tiada muat turun Excel. Sistem baharu hanya memaparkan nombor matrik, nama, foto, program, tahun pengajian dan e-mel hubungan, dan dimuat turun sebagai CSV. Muat turun direkodkan dalam log audit.
- **Akses pensyarah kepada pelajar mereka.** Dasar keselamatan peringkat baris (`student_records_instructor_select`, fungsi `util.taught_student_record_ids()`) membolehkan pensyarah melihat rekod pelajar dan maklumat individu bagi pelajar dalam seksyen mereka, dan peraturan keterlihatan aplikasi sepadan dengannya (sebelum ini, sistem asal hanya memaparkan pelajar seliaan mereka, menyebabkan nama kosong walaupun pada skrin kemasukan gred).

## Sesi kelas

- **Jana**: satu sesi kelas bagi setiap kejadian waktu kelas mingguan (hari, masa, slot masa). Pensyarah menggunakan butang **Jana daripada waktu kelas**; kakitangan menggunakan butang **Jana sesi kelas** di atas tab **Sesi kelas** (dengan halaman pengesahan) atau arahan `uv run manage.py attendance_generate_sessions {term}` (seluruh semester). Sesi kelas dan kehadiran sedia ada tidak diusik, jadi ia boleh dijalankan semula selepas waktu kelas berubah. Seksyen yang dibatalkan dilangkau.
- **Tambah sesi kelas**: kelas di luar waktu kelas, seperti kelas ganti (tarikh, mula, tamat). Hanya tarikh dalam tempoh sesi, dan hanya satu sesi kelas bagi setiap tarikh dan masa mula.
- **Batal**: membatalkan sesi kelas dengan sebab. Sesi kelas kekal tetapi dikecualikan daripada jumlah. **Pulihkan** mengembalikannya.
- Tiada kalendar cuti. Batalkan sesi kelas pada hari cuti umum (setelah kalendar semester ditambah, penjana boleh mengecualikannya).

## Memasukkan kehadiran

Di bawah **Kehadiran** bagi sesi kelas, pilih hadir, lewat, tidak hadir atau dikecualikan bagi setiap pelajar, tambah catatan (200 aksara) dan **Simpan kehadiran**. Cara terpantas ialah **Semua hadir** (menandakan semua pelajar hadir tanpa menyimpan) dan kemudian mengubah pengecualian.

- Kehadiran boleh dimasukkan mulai hari sesi kelas (bukan bagi sesi kelas akan datang atau yang dibatalkan).
- Menyimpan semula hanya merekod pelajar yang berubah, dan peristiwa audit (`attendance.recorded`) menyimpan nilai lama dan baharu bagi setiap pelajar.
- Mengosongkan status mengembalikan pelajar kepada "tidak direkodkan".
- Hanya pelajar yang berdaftar dan yang telah selesai boleh direkodkan (pelajar yang menggugurkan kursus dan menarik diri tiada dalam senarai pelajar).

## Jumlah

| Item | Takrifan |
|---|---|
| Sesi kelas diadakan | Sesi kelas yang tidak dibatalkan dan jatuh pada atau sebelum hari ini |
| Kadar kehadiran | (hadir + lewat + dikecualikan) ÷ sesi kelas diadakan × 100, satu tempat perpuluhan (separuh dibundarkan ke atas) |
| Tidak direkodkan | Sesi kelas diadakan tanpa rekod |

Tiada peraturan yang menukar bilangan tanda lewat kepada tidak hadir atau memberikan F apabila ketidakhadiran melebihi satu pertiga. Ia berbeza antara universiti, jadi pensyarah sendiri mencerminkan kehadiran dalam gred. Peraturan pengiraan terletak dalam satu perkhidmatan (`AttendanceSummary`), jadi senarai pelajar, borang kehadiran dan halaman pelajar memaparkan angka yang sama.

## PDF borang kehadiran dan CSV senarai pelajar

Kedua-dua muat turun direkodkan dalam log audit (`attendance.sheet_exported`, `attendance.roster_exported`). Nilai CSV yang bermula dengan `=`, `+`, `-` atau `@` (atau tab atau pemisah baris) dieksport dengan tanda petik tunggal di hadapan supaya ia tidak dijalankan sebagai formula.

- **Borang kehadiran (PDF)** (`/sections/{section ID}/attendance-sheet`): A4 landskap. Pelajar ke bawah, sesi kelas melintang (yang dibatalkan dikecualikan), tanda O/△/X/E dan jumlah bagi setiap pelajar. Sesi kelas yang akan datang dibiarkan kosong, jadi ia juga boleh digunakan untuk merekod secara manual. Apabila pelayan PDF (Gotenberg) tidak menjawab, "PDF tidak dapat dicipta" dipaparkan.
- **Senarai pelajar (CSV)** (`/sections/{section ID}/roster.csv`): nombor matrik, nama, program, tahun pengajian, e-mel hubungan, status pendaftaran. UTF-8 dengan BOM, jadi ia terus dibuka dalam Excel.

## Portal pelajar

**Kehadiran**: bagi setiap semester (secara lalai semester terkini yang telah bermula) dan kursus, bilangan hadir, lewat, tidak hadir dan dikecualikan serta kadar kehadiran; apabila dikembangkan, rekod bagi setiap sesi kelas yang diadakan (hanya yang dimasukkan oleh pensyarah, jika tidak "Tidak direkodkan").

## Prosedur operasi

1. Sebelum semester bermula, muktamadkan waktu kelas bagi seksyen ([bab 18](18-sections-and-timetables.md)).
2. Cipta sesi kelas dengan `uv run manage.py attendance_generate_sessions {term} --actor=...` (pensyarah juga boleh menciptanya pada skrin). Satu seksyen sahaja: `--section=CSE2010-01`; bilangan seksyen sahaja: `--dry-run` ([arahan operasi](../operations/commands.md)).
3. Jalankan semula apabila waktu kelas berubah. Sesi kelas bagi waktu yang dialih keluar tidak dipadam secara automatik; batalkannya.

## Skrin dalam pemasangan ini

Skrin dan cirinya adalah sama seperti sistem asal (Filament, Livewire); sesetengah kawalan berfungsi sedikit berbeza.

- Tab **Sesi kelas** pada skrin tukar seksyen dalam panel pentadbiran: tarikh, masa, bilik, status, rekod dimasukkan, sebab. **Batal** pada sesuatu baris membuka halaman untuk sebab, **Pulihkan** membuka halaman pengesahan. **Jana sesi kelas** ialah butang tindakan di bahagian atas skrin. Kakitangan yang hanya mempunyai `Lihat seksyen` melihat tab tersebut tanpa butang.
- Dalam portal pensyarah, **Batal** membuka medan sebab pada baris sesi kelas; masukkan sebab dan tekan **Batal** sekali lagi (menggantikan gesaan pelayar dalam sistem asal).
- Halaman kemasukan **Kehadiran** berakhir dengan `?meeting={meeting ID}`, jadi ia boleh ditanda buku. **Kembali** kembali ke senarai pelajar dan senarai sesi kelas.
- Di bawah keselamatan peringkat baris, senarai pelajar hanya diisi bagi mereka yang boleh melihat pendaftaran kursus dan rekod pelajar. Peranan lalai (Pegawai Hal Ehwal Akademik, Pembantu Jabatan) juga memegang `Lihat pendaftaran kursus dan senarai pelajar` dan `Lihat rekod pelajar`. Peranan yang hanya diberi `Rancang seksyen (pensyarah, waktu, bilik)` melihat senarai pelajar dan borang yang kosong (seperti dalam sistem asal).

[Kandungan manual pentadbir](README.md)
