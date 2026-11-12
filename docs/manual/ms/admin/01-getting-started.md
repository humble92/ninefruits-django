# 1. Bermula

## Log masuk

1. Buka `/accounts/login/` dalam pelayar anda. Membuka `/portal/` atau `/admin/` semasa belum log masuk juga membawa anda ke sini, dan selepas log masuk anda dikembalikan ke halaman yang anda minta.
2. Masukkan e-mel dan kata laluan anda, kemudian tekan **Log masuk**.
3. Jika anda telah mendaftar pengesahan dua faktor, masukkan kod 6 digit daripada aplikasi pengesah anda atau kod yang anda terima melalui e-mel.
4. Pada komputer peribadi, anda boleh memilih **Ingat peranti ini**. Kod tidak diminta sepanjang tempoh yang ditetapkan (30 hari secara lalai). Jangan pilih pilihan ini pada komputer yang dikongsi.

Jika anda terlupa kata laluan, gunakan **Terlupa kata laluan?** pada skrin log masuk untuk menerima pautan set semula. Log masuk yang gagal berulang kali akan menyekat log masuk buat sementara waktu.

Panel pentadbiran tidak mempunyai skrin log masuk sendiri. `/admin/login/` juga menghantar anda ke log masuk bersama (`/accounts/login/`).

## Portal dan panel pentadbiran

| Skrin | Alamat | Pengguna |
|---|---|---|
| Portal | `/portal/` | Semua pengguna. Laman utama (akses anda), tetapan keselamatan, dan menu bagi persona pengguna (pelajar, pensyarah, penasihat akademik, pemohon) |
| Panel pentadbiran | `/admin/` | Kakitangan yang mempunyai kebenaran `Buka panel pentadbiran` |

Kedua-dua skrin berkongsi log masuk yang sama.

- Menu portal di bahagian atas hanya memaparkan item yang sepadan dengan persona pengguna (pelajar, pensyarah, ...) dan kebenarannya. Dengan `Buka panel pentadbiran`, item **Pentadbiran** membawa anda ke panel pentadbiran.
- Menu pengguna di penjuru kanan atas panel pentadbiran memaut ke **Pengesahan dua faktor** (tetapan keselamatan portal) dan ke **Portal**, serta melog keluar anda (**Log keluar**). Halaman pertama (**Papan pemuka**) memaparkan nama dan e-mel akaun, pautan portal dan butang log keluar.
- Membuka alamat panel pentadbiran dengan akaun yang tidak mempunyai kebenaran tersebut memaparkan "403 Forbidden".

Menu di sebelah kiri panel pentadbiran bergantung pada kebenaran anda. Menu ini mengekalkan susunan kumpulan asal (Pelajar dan kakitangan, Kemasukan, Kurikulum dan seksyen, Pendaftaran kursus, Gred, Penilaian kursus, Peperiksaan, Sijil, Pengijazahan, Laporan, Integrasi LMS, Data rujukan, Pengguna dan akses, Audit, Tetapan); kumpulan yang tidak mengandungi sebarang skrin yang boleh anda buka tidak dipaparkan. Jika sesuatu menu tiada, minta penetapan peranan daripada pentadbir sistem. Medan carian di atas menu mencari entri menu mengikut nama.

## Notis dua faktor

Apabila dasar dua faktor ialah "disyorkan", atau semasa tempoh tangguh bagi dasar yang diwajibkan, notis dipaparkan di bahagian atas portal dan panel pentadbiran. **Sediakan sekarang** membuka halaman keselamatan portal. Lihat [3. Pengesahan dua faktor](03-two-factor-authentication.md).

## Bahasa

Tukar bahasa dengan pemilih bahasa di bahagian atas portal (skrin log masuk mempunyai pemilih yang sama) atau dengan senarai bahasa dalam menu pengguna panel pentadbiran. Apabila anda menukarnya semasa log masuk, pilihan itu disimpan pada akaun anda dan dikekalkan untuk log masuk seterusnya. Pentadbir sistem menentukan bahasa yang ditawarkan di bawah **Tetapan > Institusi**.
