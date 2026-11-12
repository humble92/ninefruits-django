# 7. Unit organisasi dan program

Menu: **Data rujukan > Jenis unit organisasi**, **Unit organisasi**, **Program**

## Unit organisasi

Universiti, fakulti, jabatan, major dan pejabat pentadbiran diurus pada satu skrin. Ia menggantikan fakulti (`SFCOLLEGE`) dan jabatan (`SFDEPARTMENT`) dalam sistem lama (YUSTIC).

| Medan | Penerangan |
|---|---|
| Kod | Kod pengenalan kekal, contohnya `CSE` |
| Jenis | Universiti, fakulti, jabatan, dsb. (jenis lain boleh ditambah pada skrin Jenis unit organisasi) |
| Nama, Nama ringkas | Mengikut bahasa |
| Induk | Unit tempat unit ini bernaung. Sesuatu unit tidak boleh dipindahkan ke bawah dirinya sendiri atau ke bawah salah satu unit keturunannya |
| Sah dari, Sah hingga | Tempoh unit itu wujud. Tarikh tamat yang kosong bermaksud unit itu masih beroperasi |

- Senarai memaparkan **Sah pada masa ini sahaja** secara lalai. Matikan penapis untuk turut melihat unit lampau.
- Apabila sesuatu unit organisasi dipilih sebagai skop penetapan peranan, setiap unit di bawahnya turut dirangkumi. Contoh: skop Fakulti Kejuruteraan = setiap jabatan dalam Fakulti Kejuruteraan.

## Penstrukturan semula

Rekod pelajar dan gred lampau mesti merujuk unit sebagaimana keadaannya pada waktu itu, jadi sesuatu unit tidak disunting secara langsung; perubahan itu direkodkan sebagai **penstrukturan semula**.

1. Buka halaman **Sunting** bagi unit yang hilang (atau berubah).
2. Tekan **Susun semula**.
3. Pilih jenis perubahan.
   - **Ditukar nama**: cipta unit dengan nama baharu terlebih dahulu dan tetapkannya sebagai pengganti
   - **Digabungkan**: apabila beberapa unit bergabung menjadi satu, tetapkan pengganti yang sama daripada setiap unit
   - **Dipecahkan**: apabila satu unit dibahagikan kepada beberapa unit, tetapkan beberapa pengganti
   - **Dipindahkan**: apabila unit itu dipindahkan ke bawah induk lain sebagai unit baharu
4. Masukkan **Tarikh berkuat kuasa** dan sebab. Unit itu tamat sehari sebelum tarikh berkuat kuasa, dan rekodnya muncul dalam senarai **Pengganti** di bawah.

Kesilapan ejaan yang mudah dibetulkan dengan **menyunting** nama, bukan melalui penstrukturan semula (perubahan data itu direkodkan).

## Program

Program ijazah atau program major. Rekod pelajar dimiliki oleh sesuatu program ([bab 12](12-people-and-student-records.md)).

| Medan | Penerangan |
|---|---|
| Kod, Nama, Nama ijazah | Contoh nama ijazah: Sarjana Muda Kejuruteraan |
| Peringkat ijazah | Diploma, Sarjana Muda, Sarjana, Doktor Falsafah, Sijil, Bukan ijazah |
| Unit organisasi | Jabatan yang mengendalikan program itu |
| Tempoh standard (tahun) | Tempoh standard untuk tamat pengajian (tahun) |
| Sah dari, Sah hingga | Tempoh program itu wujud, bukan tempoh program itu menerima pelajar baharu |
| Menerima major kedua, Menerima minor | Sama ada pelajar program lain boleh memohon program ini sebagai major kedua atau minor ([bab 19](19-second-majors-and-minors.md)) |
