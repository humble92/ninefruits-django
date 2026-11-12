# 10. Tahun akademik, semester, tempoh urusan

Menu: **Data rujukan > Tahun akademik**, **Jenis semester**, **Semester**, **Slot masa** (kebenaran `Urus tahun akademik, semester, jenis semester dan slot masa`; tempoh urusan memerlukan `Urus tempoh urusan`)

## Perbezaan daripada sistem lama

Sistem lama (YUSTIC) menentukan "semester semasa" dengan satu bendera status semester (`AFS_CHECK`), yang menyukarkan pemprosesan gred semester lalu dan pendaftaran kursus semester akan datang pada masa yang sama. Sistem baharu tidak mempunyai tetapan "semester semasa". Sebaliknya, setiap tugas melihat **tempoh urusan** yang dibuka untuk menentukan semester yang berkenaan. Kemasukan gred bagi semester lalu, kelas dalam semester semasa dan pendaftaran kursus bagi semester akan datang tidak menghalang satu sama lain.

## Tahun akademik dan semester

1. **Tahun akademik**: kod (contohnya `2026`), nama, tarikh mula/tamat. Tahun akademik tidak boleh bertindih.
2. **Jenis semester**: semester pertama, semester kedua, semester pendek (musim panas/musim sejuk), dsb. Bendera **Semester biasa** digunakan kemudian oleh peraturan seperti had kredit.
3. **Semester**: tahun akademik, jenis semester, kod (contohnya `2026-FA`, untuk paparan sahaja), nama, tarikh mula/tamat kelas. Semester daripada jenis yang sama tidak boleh mempunyai tempoh kelas yang bertindih.

## Status semester

| Status | Maksud | Tempoh urusan |
|---|---|---|
| Dirancang | Dalam persediaan. Tidak kelihatan kepada pelajar | Tidak dibuka |
| Diterbitkan | Sedang beroperasi | Dibuka |
| Gred ditutup | Selepas gred dimuktamadkan | Dibuka (rayuan gred, dsb.) |
| Diarkibkan | Telah tamat | Tidak dibuka |

Status hanya berubah melalui **Tukar status** pada halaman **Sunting** semester. Urutannya ialah Dirancang → Diterbitkan → Gred ditutup → Diarkibkan; Diterbitkan dan Gred ditutup boleh dikembalikan satu langkah. Perubahan direkodkan bersama sebab.

## Sesi

Sesi ialah tempoh dalam sesuatu semester ketika kelas berjalan. Uruskannya pada tab **Sesi** di halaman **Sunting** semester.

- Mencipta semester akan mencipta sesi **Semester penuh** (kod `FULL`) secara automatik; sesi ini mengikut tarikh semester apabila tarikh itu berubah.
- Tambah sesi apabila sesetengah kursus hanya berjalan sebahagian daripada semester, seperti kursus 8 minggu separuh pertama dan separuh kedua atau kursus intensif 3 minggu. Contoh: `A` separuh pertama 1/9–25/10, `B` separuh kedua 26/10–20/12, `I` intensif 1/11–21/11.
- Sesi mesti berada dalam lingkungan semester. Jika anda memendekkan semester, betulkan dahulu sesi yang akan terkeluar daripadanya.
- Setiap seksyen tergolong dalam satu sesi ([bab 18](18-sections-and-timetables.md)). Universiti yang tidak menggunakan sesi hanya memerlukan sesi semester penuh.

## Tempoh urusan

Tambahkannya di bawah **Tempoh urusan** di bahagian bawah halaman **Sunting** semester.

| Medan | Penerangan |
|---|---|
| Tempoh | Troli pendaftaran, Pendaftaran kursus, Tambah/gugur, Tarik diri kursus, Kemasukan gred, Rayuan gred, Penilaian kursus, Permohonan bergraduat, Permohonan major kedua dan minor |
| Sesi | Hanya bagi tempoh berkaitan kursus (tambah/gugur, tarik diri, kemasukan gred, rayuan gred, penilaian kursus). Lalai ialah sesi semester penuh |
| Dibuka, Ditutup | Masa dalam zon waktu institusi. Tempoh ditutup pada masa penutupan |
| Kelayakan | Kosong bermaksud semua orang. Gabungkan tahun pengajian, julat tahun kemasukan, program dan unit organisasi (termasuk unit keturunan). Pelajar mesti memenuhi setiap syarat |

Terdapat dua jenis tempoh.

| Jenis | Tempoh | Rujukan |
|---|---|---|
| Tempoh berkaitan kursus | Tambah/gugur, Tarik diri kursus, Kemasukan gred, Rayuan gred, Penilaian kursus | Sesi tempat kursus itu tergolong. Kursus separuh kedua mengikut tempoh tambah/gugur, tarik diri dan penggredan bagi sesi separuh kedua |
| Tempoh pelajar/semester | Troli pendaftaran, Pendaftaran kursus, Permohonan bergraduat, Permohonan major kedua dan minor | Seluruh semester. Tiada sesi |

**Mencipta tempoh mengikut sesi**: pada tab Sesi, tekan **Salin tempoh** pada sesuatu sesi untuk menyalin tempoh kursus daripada sesi lain (biasanya semester penuh), dianjakkan ke tarikh sesi ini. Tempoh awal (tambah/gugur, tarik diri) mengekalkan jaraknya dari tarikh mula sesi; tempoh lewat (kemasukan gred, penilaian kursus) mengekalkan jaraknya dari tarikh tamat sesi. Semak dan laraskannya selepas menyalin.

**Contoh pembukaan berperingkat**: cipta tiga tempoh pendaftaran kursus.

| Tempoh | Dibuka | Kelayakan |
|---|---|---|
| Pendaftaran kursus | 10 Februari 10:00 | Tahun 4 |
| Pendaftaran kursus | 11 Februari 10:00 | Tahun 3 |
| Pendaftaran kursus | 12 Februari 10:00 | Tahun 1, 2 |

Tahun pengajian dan tahun kemasukan setiap pelajar diambil daripada data rekod pelajar ([bab 12](12-people-and-student-records.md)).

## Slot masa

Unit masa kelas. Tetapkan kod (contohnya `1`), nama (Slot 1), masa mula/tamat dan hari. Semasa memasukkan waktu kelas seksyen, memilih slot masa akan mengisi masa mula dan tamat. Profil universiti Korea memuatkan sepuluh slot 50 minit bermula 09:00 (Isnin hingga Jumaat).

Masa slot ialah masa "jam dinding" yang tidak bergantung pada zon waktu; ia disimpan tepat seperti yang dimasukkan.

Masa pembukaan dan penutupan tempoh urusan dimasukkan dan dipaparkan dalam zon waktu institusi di panel pentadbiran dan disimpan dalam UTC.
