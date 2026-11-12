# 12. Individu dan rekod pelajar

Menu: **Pelajar dan kakitangan > Individu**, **Rekod pelajar**, **Pensyarah**

## Hubungan antara individu dan rekod pelajar

| Konsep | Penerangan |
|---|---|
| Individu | Seorang manusia. Nama, tarikh lahir, butiran perhubungan, nombor pengenalan, foto, penjaga. Sama ada pelajar atau pensyarah, seorang manusia ialah satu individu |
| Rekod pelajar | Satu kemasukan. Nombor matrik, program, tarikh kemasukan, tahun pengajian, status. Pelajar yang bergraduat dan kemudian mendapat kemasukan semula menerima **rekod pelajar baharu (nombor matrik baharu)** pada individu yang sama |
| Pensyarah | Butiran pensyarah bagi individu itu (nombor pekerja, unit organisasi, jenis perkhidmatan, jawatan akademik). Satu bagi setiap individu |
| Akaun | Akaun log masuk. Dipautkan 1:1 dengan individu. Individu yang mempunyai beberapa rekod pelajar tetap mempunyai satu akaun |

Pelajar dan graduan memilih rekod pelajar dalam portal (apabila terdapat beberapa rekod, pemilih rekod dipaparkan di bahagian atas).

## Individu

- Setiap individu mempunyai **Nama dalam huruf Rumi** (nama sah seperti dalam pasport: nama keluarga, nama diri) dan **Nama dalam bahasa lain** (contohnya bahasa Korea `김민수`). Skrin memaparkan nama dalam bahasa semasa jika ada, jika tidak nama dalam huruf Rumi. Carian menemui kedua-duanya.
- Nombor kad pengenalan dan nombor pasport disimpan secara tersulit dan dipaparkan secara bertopeng. Nilai penuh dipaparkan sekali pada halaman berasingan selepas menekan **Papar nombor kad pengenalan** (atau **Papar nombor pasport**) di bahagian atas halaman individu dan memasukkan sebab (kebenaran `Dedahkan nombor kad pengenalan dan pasport`). Nilai itu tidak disimpan di mana-mana (tiada mesej atau log), dan pendedahan itu ditulis ke log keselamatan bersama sebabnya. Carian mengikut nombor hanya menemui padanan tepat.
- Foto dimuat naik pada halaman sunting individu. Foto hanya boleh dimuat turun selepas semakan kebenaran (tiada alamat awam).
- Penjaga diurus pada tab **Penjaga** di halaman butiran individu. Pelajar juga boleh menyunting penjaga dan butiran perhubungan mereka (e-mel, telefon, alamat, poskod) di bawah **Butiran saya** dalam portal. Mereka tidak boleh menukar nama, tarikh lahir atau nombor pengenalan.
- **Sejarah perubahan** di bahagian bawah halaman individu menyenaraikan 50 perubahan data terkini bagi individu itu dan penjaganya (masa, jadual, lajur yang berubah, pengguna). Dengan `Lihat rekod audit`, anda boleh membuka setiap perubahan (nilai sebelum dan selepas). Halaman rekod pelajar memaparkan sejarah rekod itu, perubahan statusnya, penasihat akademik serta major kedua dan minornya dengan cara yang sama.

| Kebenaran | Perkara yang dibenarkan |
|---|---|
| `Lihat semua individu` | Melihat setiap individu |
| `Cipta dan sunting individu` | Mencipta dan menyunting individu |
| `Dedahkan nombor kad pengenalan dan pasport` | Melihat nombor kad pengenalan dan pasport penuh |
| `Gabungkan individu pendua`, `Jemput individu untuk mencipta akaun` | [Bab 14](14-merge-and-invitations.md) |

Kakitangan tanpa kebenaran `Lihat semua individu` masih boleh melihat individu dan pensyarah di sebalik rekod pelajar yang dibenarkan untuk mereka lihat.

## Mendaftar pelajar

1. Tekan **Tambah rekod pelajar** di bahagian atas senarai **Rekod pelajar** (tajuk halaman ialah **Daftar pelajar**).
2. Pilih **Individu sedia ada** (kemasukan semula, pensyarah yang menyambung ke pengajian siswazah, dsb.) atau masukkan **Individu baharu**. Sebelum mencipta individu baharu, buat carian untuk memastikan sama ada individu yang sama sudah wujud.
3. Masukkan program, tarikh kemasukan, tahun pengajian dan jenis kemasukan. Unit organisasi pengurus diambil daripada program.
4. Biarkan nombor matrik kosong untuk menjananya dengan corak nombor matrik di bawah **Tetapan > Rekod pelajar**. Corak lalai `{YYYY}{SEQ:5}` ialah tahun kemasukan diikuti jujukan 5 digit (contohnya `202600001`). Nombor yang sudah digunakan (termasuk rekod yang diimport) dilangkau.

| Token nombor matrik | Maksud |
|---|---|
| `{YYYY}` | Tahun kemasukan |
| `{YY}` | Dua digit terakhir tahun kemasukan |
| `{SEQ:n}` | Jujukan yang diisi hingga n digit. Corak mesti mengandungi tepat satu. Dikira secara berasingan bagi setiap awalan (contohnya `2026`) |

Nombor matrik dan status sesuatu rekod tidak ditukar pada halaman sunting. Status berubah melalui perubahan status ([bab 13](13-status-changes-and-advisors.md)).

## Skop paparan rekod pelajar

| Skop kebenaran | Rekod pelajar yang boleh anda lihat |
|---|---|
| `Lihat rekod pelajar` atau `Cipta dan sunting rekod pelajar`, skop Semua | Setiap rekod pelajar |
| Skop unit organisasi | Rekod dalam unit itu dan unit keturunannya (contohnya skop Fakulti Kejuruteraan = setiap jabatan dalam fakulti itu) |
| Skop program | Rekod dalam program itu |
| Skop unit organisasi atau program (major kedua dan minor) | Rekod pelajar yang mengikuti unit atau program itu sebagai major kedua atau minor (lihat sahaja) |
| Pelulus major kedua dan minor | Rekod pelajar yang menghantar permohonan untuk diputuskan (lihat sahaja) |
| Penasihat akademik | Pelajar seliaan semasa |
| Pelajar itu sendiri | Rekod mereka sendiri |

Peraturan yang sama wujud dalam pangkalan data (keselamatan peringkat baris), jadi pertanyaan di luar skrin (laporan, sambungan terus) juga tidak boleh melampaui skop.

## Pensyarah

Dengan **Tambah pensyarah** di bahagian atas senarai **Pensyarah** (tajuk halaman ialah **Pensyarah baharu**), pilih individu sedia ada atau masukkan individu baharu (kebenaran `Urus pensyarah`). Setelah tarikh tamat berlalu, pensyarah itu tidak lagi tersenarai dalam senarai pensyarah semasa (penapis lalai) dan pemilih penasihat akademik.

## Memuatkan data yang banyak sekali gus dengan CSV

Gunakan **Import CSV** di bahagian atas senarai rekod pelajar dan senarai pensyarah. Format lajur terdapat dalam [bab 9](09-csv-import.md#pelajar-dan-pensyarah).
