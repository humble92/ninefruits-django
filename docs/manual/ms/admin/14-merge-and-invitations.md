# 14. Penggabungan individu dan jemputan akaun

Menu: **Pelajar dan kakitangan > Individu**, kemudian **Gabungkan pendua** dan **Jemput untuk mencipta akaun** di bahagian atas halaman butiran individu

## Menggabungkan individu pendua

Digunakan apabila manusia yang sama didaftarkan sebagai dua individu (contohnya kemasukan semula yang individu sedia adanya tidak ditemui lalu individu baharu dicipta). Memerlukan kebenaran `Gabungkan individu pendua`.

1. Cari calon: cari dalam senarai individu bagi nama dan tarikh lahir yang sama, atau nombor kad pengenalan yang sama. Pengendali IT boleh menghasilkan senarai calon penuh dengan `uv run manage.py people_find_duplicates`.
2. Pada halaman butiran **individu yang akan dibuang (pendua)**, tekan **Gabungkan pendua**, pilih individu di bawah **Kekalkan individu ini** daripada senarai, dan masukkan sebab. Apabila penggabungan selesai, anda dibawa ke halaman individu yang dikekalkan.
3. Rekod pelajar, permohonan, butiran pensyarah, penjaga dan akaun milik individu yang dibuang dipindahkan kepada individu yang dikekalkan. Jika kedua-duanya mempunyai akaun, akaun individu yang dibuang dinyahaktifkan dan log masuk institusi yang dipautkan kepadanya dipindahkan jika boleh.
4. Individu yang dibuang kekal sebagai **Digabungkan** (penapis senarai **Digabungkan**) supaya rekod lama masih boleh ditemui. Individu itu tidak boleh digunakan untuk rekod pelajar baharu.

- Jika kedua-dua individu mempunyai butiran pensyarah, penggabungan ditolak. Kemas kini butiran pensyarah terlebih dahulu.
- Jika kedua-dua individu mempunyai permohonan terbuka dalam pengambilan yang sama, penggabungan ditolak. Minta pemohon menarik balik salah satu permohonan.
- **Tindakan ini tidak boleh dibatalkan.** Sentiasa semak rekod pelajar dan tarikh lahir sebelum menggabungkan. Penggabungan ditulis ke log aktiviti bersama sebabnya.

## Jemputan akaun

Menghantar e-mel jemputan kepada individu yang belum mempunyai akaun, seperti pelajar dan pensyarah yang dimuatkan melalui CSV. Memerlukan kebenaran `Jemput individu untuk mencipta akaun`.

1. Pada halaman butiran individu, tekan **Jemput untuk mencipta akaun** dan masukkan e-mel log masuk (biasanya e-mel peribadi).
2. Apabila penerima menetapkan kata laluan melalui pautan dalam e-mel, akaun dicipta dan mereka terus dilog masuk.

- Pautan sah selama tempoh yang ditetapkan di **Tetapan > Rekod pelajar > Pautan jemputan sah selama (hari)** (lalai 14 hari).
- Menghantar semula akan membatalkan pautan sebelumnya.
- Anda tidak boleh menjemput individu yang sudah mempunyai akaun, atau menggunakan e-mel yang digunakan oleh akaun lain.
- Akaun yang sama dikekalkan selepas bergraduat. Minta individu yang hanya menggunakan e-mel institusi untuk menukar e-mel log masuk mereka kepada alamat peribadi ([bab 15](15-sign-in-methods.md)).
