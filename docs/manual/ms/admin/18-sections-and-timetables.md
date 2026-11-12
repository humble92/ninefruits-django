# 18. Seksyen dan Jadual Waktu

Menu: **Kurikulum dan seksyen > Seksyen**, **Jadual waktu** (kebenaran `Lihat seksyen`, `Rancang seksyen (pensyarah, waktu, bilik)`. Apabila ditetapkan dengan skop unit organisasi, ia hanya meliputi seksyen yang ditawarkan oleh unit tersebut)

## Mencipta seksyen

1. Di bawah **Seksyen > Cipta**, masukkan sesi semester, kursus, nombor seksyen (cth. `01`), kapasiti dan unit penawar. Nama kursus dan kredit diambil daripada versi kursus yang berkuat kuasa pada tarikh mula sesi.
2. Dalam tab skrin suntingan, masukkan **Waktu kelas**, **Pensyarah** dan **Tempat simpanan**.
3. Apabila semuanya sedia, **Terbitkan** seksyen itu. Hanya seksyen yang diterbitkan muncul dalam **Katalog kursus** portal dan boleh didaftarkan ([bab 20](20-registration.md)).

| Status | Maksud |
|---|---|
| Draf | Sedang dirancang. Hanya kakitangan dan pensyarah yang ditetapkan dapat melihatnya |
| Diterbitkan | Boleh dilihat oleh pelajar. Boleh dihantar **Kembali ke draf** |
| Dibatalkan | Sebab diwajibkan. Waktu bilik dan pensyarah dibebaskan. **Buka semula** mengembalikannya kepada draf; jika seksyen lain telah mengambil waktu tersebut dalam pada itu, ia tidak boleh dibuka semula |

Hanya seksyen draf boleh dipadam. Seksyen yang pernah diterbitkan dibatalkan sebaliknya.

| Medan | Keterangan |
|---|---|
| Sesi | Sesi bagi semester ([bab 10](10-terms.md)). Berpindah ke sesi lain mengubah tarikh kelas dan versi kursus supaya sepadan dengan sesi tersebut |
| Siapa boleh mendaftar, Siapa tidak boleh mendaftar | Tahun pengajian, tahun kemasukan, program, unit organisasi. Contoh: mengecualikan pelajar major kursus itu sendiri daripada kursus pendidikan umum. Pelajar major kedua dan minor juga dikira sebagai pelajar program tersebut |
| Bahasa pengantar | cth. `ko`, `en` |
| Saiz senarai menunggu | Bilangan entri senarai menunggu yang diterima setelah seksyen penuh. 0: tiada senarai menunggu ([bab 20](20-registration.md)) |
| Penilaian (kaedah penilaian) | Penilaian mutlak (lalai; pensyarah memasukkan markah dan gred dikira daripadanya) atau penilaian relatif (hanya gred dimasukkan, had gred terpakai). Pensyarah memohon perubahan daripada skrin kemasukan gred dan kakitangan seksyen meluluskannya. Ia tidak boleh diubah setelah gred dimasukkan ([bab 21](21-grades.md)). Turut disalin apabila menyalin semester |

## Waktu kelas dan bilik

Dalam tab **Waktu kelas**, masukkan hari, masa mula dan tamat serta bilik. Memilih **Slot masa** akan mengisi masa secara automatik. Biarkan tarikh kelas kosong untuk menggunakan tarikh sesi.

- Dua seksyen tidak boleh menggunakan bilik yang sama pada masa yang sama, dan seorang pensyarah tidak boleh mengajar dua seksyen pada masa yang sama. Pangkalan data menguatkuasakan perkara ini; skrin memaparkan seksyen yang bercanggah, cth. "Bilik ini sudah ditempah pada waktu ini oleh OOO".
- Apabila tarikh tidak bertindih, seperti separuh pertama dan separuh kedua semester, masa dan bilik yang sama boleh digunakan.
- Seksyen yang dibatalkan tidak menduduki sebarang waktu.

## Pensyarah

Dalam tab **Pensyarah**, tetapkan pensyarah dengan peranan (Pensyarah, Pensyarah bersama, Pembantu pengajar). Sesuatu seksyen boleh mempunyai beberapa orang pensyarah. Pensyarah yang sudah mengajar seksyen lain pada masa yang sama tidak boleh ditetapkan. Pensyarah mengurus jadual waktu dan rangka kursus dalam portal di bawah **Pengajaran saya**.

## Tempat simpanan

Dalam tab **Tempat simpanan**, simpan tempat bagi kumpulan pelajar (cth. 30 tempat bagi pelajar major program tersebut). Selepas masa **Dibuka kepada semua pada**, tempat yang tidak digunakan boleh diambil oleh sesiapa sahaja. Jumlah tempat simpanan tidak boleh melebihi kapasiti. Ia diguna pakai semasa pendaftaran kursus ([bab 20](20-registration.md)).

## Rangka kursus

Pensyarah menulisnya dalam portal di bawah **Pengajaran saya** (ia juga dibuka daripada butang **Rangka kursus** pada skrin seksyen). Mereka memasukkan gambaran keseluruhan, objektif pembelajaran, buku teks dan bahan, dasar kursus, penilaian (item dan pemberat) serta rancangan mingguan; setelah **Diterbitkan**, ia boleh dilihat oleh pelajar.

## Menyalin daripada semester lain

**Salin daripada semester lain** dalam senarai seksyen bermula daripada perancangan semester terdahulu (biasanya semester yang sama pada tahun lepas). Semak hasilnya dengan **Pratonton sahaja** terlebih dahulu.

- Seksyen yang tidak dibatalkan dan berada dalam skop anda disalin sebagai draf.
- Turut disalin: pensyarah yang masih berkhidmat, waktu kelas dan bilik, tempat simpanan (masa pembukaan dianjakkan mengikut perbezaan tarikh mula semester), rangka kursus (sebagai draf yang belum diterbitkan).
- Sesi dipadankan mengikut kod (seluruh semester jika tiada). Versi kursus diambil mengikut tarikh mula sesi baharu.
- Seksyen yang nombor seksyennya sudah wujud dalam semester sasaran dilangkau; apabila bilik sudah diambil, seksyen disalin tanpa bilik. Pemberitahuan hasil menyenaraikan seksyen yang dilangkau dan seksyen yang perlu disemak.

Pengendali IT boleh melakukan perkara yang sama dengan `uv run manage.py section_copy`.

## Jadual waktu dan semakan

- **Jadual waktu**: pilih semester dan bilik atau pensyarah untuk melihat jadual waktu mingguan.
- Semakan sebelum penerbitan: pengendali IT menjalankan `uv run manage.py schedule_check_conflicts <term code>` untuk mencari bilik yang lebih kecil daripada kapasiti, pensyarah yang telah bersara, ketidakpadanan versi kursus dan tempat simpanan yang melebihi kapasiti ([rujukan arahan](../operations/commands.md#schedule_check_conflicts)).

## Skop

Senarai dan skrin hanya memaparkan seksyen bagi unit penawar yang berada dalam skop `Lihat seksyen` dan `Rancang seksyen (pensyarah, waktu, bilik)`. Tab waktu kelas, pensyarah dan tempat simpanan serta butang status (Terbitkan, Kembali ke draf, Batalkan seksyen, Buka semula) memerlukan `Rancang seksyen (pensyarah, waktu, bilik)` dalam skop yang meliputi unit penawar seksyen itu. Halaman jadual waktu bermula dengan semester yang sedang berjalan (jika tiada, semester seterusnya). Pada telefon, ia memaparkan senarai mengikut hari dalam minggu.

[Kandungan manual pentadbir](README.md)
