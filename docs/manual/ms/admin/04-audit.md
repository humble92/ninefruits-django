# 4. Audit

Tiga skrin di bawah menu **Audit** adalah baca sahaja; tiada sesiapa boleh menyunting atau memadamkannya (memerlukan kebenaran `Lihat rekod audit` dan `Lihat peristiwa keselamatan`). Senarai tidak mempunyai butang tambah, ubah atau padam; membuka sesuatu baris memaparkan butirannya secara baca sahaja.

| Skrin | Apa yang dipaparkan | Contoh |
|---|---|---|
| Log aktiviti | Siapa melakukan apa, dan **mengapa**. Sebab dan butiran | Penetapan peranan (sebab: mengganti tugas sepanjang semester), perubahan kebenaran (senarai ditambah/dibuang), perubahan tetapan (sebelum/selepas), arahan yang dijalankan |
| Perubahan data | Nilai sebelum dan selepas bagi baris jadual. Perubahan terus yang memintas aplikasi turut direkodkan | `users` UPDATE, lajur yang berubah `locale` |
| Peristiwa keselamatan | Log masuk, log masuk gagal, pengesahan dua faktor, peristiwa berkaitan kebenaran, perubahan kata laluan dan e-mel, pemangkasan audit (`audit_prune`) | Log masuk gagal (nama log masuk, IP) |

## Cara membacanya

- Lajur **Pengguna**: tindakan yang dibuat pada skrin menunjukkan nama pengguna atau `user:nombor`, tugas automatik (Celery) menunjukkan `system:task:...`, arahan menunjukkan `system:command:...`.
- Kata laluan, rahsia dua faktor dan nilai seumpamanya disembunyikan sebagai `[redacted]`.
- Rekod yang mempunyai **ID permintaan** yang sama dicipta oleh satu permintaan skrin. Mencari ID permintaan yang sama merentas skrin akan menunjukkan jejak penuh bagi satu tindakan. Larian arahan menggunakan ID larian yang bermula dengan `cmd-`.

## Carian lazim

Pilih syarat di bawah **Tapisan** di penjuru kanan atas senarai dan taipkan nilai dalam medan carian.

| Apa yang ingin diketahui | Cara |
|---|---|
| Bila kebenaran seseorang pengguna berubah | Dalam log aktiviti, log `security`, peristiwa `role.assigned`, `role.assignment_revoked` |
| Akaun yang banyak log masuk gagal | Dalam peristiwa keselamatan, tapis mengikut peristiwa `Log masuk gagal`, lihat lajur nama log masuk |
| Siapa menukar dasar keselamatan | Peristiwa log aktiviti `settings.updated` |
| Bagaimana sesuatu baris tertentu berubah | Dalam perubahan data, tapis mengikut jadual dan cari mengikut ID rekod |
