# 3. Pengesahan dua faktor

## Cara pengguna mendaftar

Pengguna mendaftar pada halaman **Keselamatan** di portal (`/portal/security/`, menu pengguna **Pengesahan dua faktor** dalam panel pentadbiran). Kata laluan disahkan sekali lagi sebelum mendaftar atau menyahaktifkan.

### Aplikasi pengesah (disyorkan)

1. Tekan **Aktifkan pengesahan dua faktor**.
2. Imbas kod QR dengan aplikasi pengesah seperti Google Authenticator atau Microsoft Authenticator.
3. Masukkan kod 6 digit yang dipaparkan dalam aplikasi dan tekan **Sahkan**.
4. Simpan **kod pemulihan** yang dipaparkan pada skrin di tempat yang selamat. Setiap kod boleh digunakan sekali jika telefon hilang.

### Kod e-mel

Dipaparkan hanya apabila pentadbir sistem membenarkannya. Kaedah ini bertujuan untuk pengguna yang tidak dapat menggunakan aplikasi pengesah dan kurang selamat berbanding aplikasi pengesah.

1. Di ruangan **Kod e-mel**, tekan **Hantar kod untuk persediaan**.
2. Masukkan kod 6 digit yang dihantar ke e-mel akaun dan tekan **Sahkan**.
3. Selepas itu, kod akan dihantar melalui e-mel pada setiap log masuk. Kod boleh digunakan sekali dalam tempoh 10 minit; selepas 5 percubaan yang salah, kod baharu diperlukan. Kod boleh dihantar sekali seminit dan sehingga 5 kali sejam.

Kedua-dua kaedah boleh didaftarkan. Apabila dasarnya "wajib", kaedah terakhir yang tinggal tidak boleh dinyahaktifkan.

## Tetapan dasar (pentadbir sistem)

Ditetapkan di bawah **Tetapan > Keselamatan** dalam panel pentadbiran. Simpanan berkuat kuasa kepada setiap pengguna mulai pemuatan halaman seterusnya.

| Tetapan | Penerangan |
|---|---|
| Dasar | **Tidak digunakan** / **Disyorkan (pilihan)**: pengguna yang belum mendaftar hanya melihat notis / **Wajib bagi peranan terpilih**: pengguna yang memegang peranan terpilih mesti mendaftar / **Wajib bagi semua** |
| Peranan yang wajib menggunakan pengesahan dua faktor | Dipilih apabila dasarnya "Wajib bagi peranan terpilih" |
| Tempoh tangguh (hari) | Tempoh pengguna boleh terus bekerja tanpa mendaftar selepas syarat itu mula terpakai kepadanya. Sepanjang tempoh ini, notis tarikh akhir dipaparkan di bahagian atas portal dan panel pentadbiran. Selepas tempoh itu berlalu, hanya halaman keselamatan boleh digunakan. 0 bermaksud serta-merta |
| Ingat peranti selama (hari) | Tempoh kod tidak diminta pada peranti yang telah memilih **Ingat peranti ini**. 0 mematikan ciri ini |
| Benarkan kod melalui e-mel | Apabila dimatikan, kod e-mel tidak dikira sebagai pengesahan dua faktor. Pengguna yang hanya mendaftar kod e-mel akan diminta mendaftar aplikasi pengesah mengikut dasar |

Cadangan operasi: **Wajib bagi peranan terpilih** untuk peranan kakitangan (Pejabat Pendaftar, hal ehwal akademik, pentadbir sistem, dsb.), disyorkan untuk pelajar.

## Set semula (telefon hilang, dsb.)

1. Buka pengguna di bawah **Pengguna dan akses > Pengguna**.
2. Tekan **Set semula pengesahan dua faktor** di bahagian atas halaman dan masukkan sebab (memerlukan kebenaran `Set semula pengesahan dua faktor`).
3. Aplikasi pengesah, kod pemulihan, kod e-mel dan peranti yang diingati milik pengguna itu semuanya dikosongkan. Tempoh tangguh bermula semula.

Anda tidak boleh menetapkan semula akaun anda sendiri. Set semula direkodkan bersama sebabnya sebagai peristiwa keselamatan dan dalam log aktiviti.

Jika satu-satunya pentadbir kehilangan telefon dan tidak dapat mengakses panel pentadbiran, pengendali IT menetapkannya semula dengan `uv run manage.py security_reset_mfa` (Docker: `docker compose exec app uv run manage.py security_reset_mfa`, [rujukan arahan](../operations/commands.md)).
