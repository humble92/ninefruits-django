# 15. Kaedah log masuk

Menu: **Tetapan > Kaedah log masuk** (kebenaran `Urus kaedah log masuk dan SSO`)

## Nama log masuk

E-mel akaun ialah nama log masuk lalai. Apabila log masuk dengan nombor matrik dihidupkan, medan pada skrin log masuk bertukar menjadi "E-mel atau nombor matrik".

| Log masuk dengan nombor matrik | Tingkah laku |
|---|---|
| Tidak dibenarkan | E-mel sahaja |
| Pelajar semasa sahaja | Nombor matrik bagi rekod yang sedang belajar dan tangguh pengajian boleh log masuk |
| Pelajar semasa dan graduan | Nombor matrik bagi rekod yang telah tamat (bergraduat, tarik diri, dan sebagainya) juga boleh log masuk |

Individu yang mempunyai beberapa rekod pelajar akan sampai ke akaun yang sama tanpa mengira nombor matrik yang digunakan.

## Penguncian akaun

| Tetapan | Keterangan |
|---|---|
| Kunci selepas cubaan gagal | Akaun dikunci apabila kata laluan yang salah dimasukkan sebanyak bilangan ini berturut-turut. 0 mematikan penguncian |
| Tempoh kunci (minit) | Kunci ditarik balik secara automatik selepas tempoh ini |

Cubaan melalui e-mel dan melalui nombor matrik dikira sebagai kegagalan bagi akaun yang sama. Akaun yang dikunci menerima mesej yang sama seperti kata laluan yang salah, jadi ia tidak mendedahkan sama ada akaun itu wujud. Penguncian direkodkan sebagai peristiwa keselamatan (**Log masuk dikunci**).

Untuk menarik balik kunci lebih awal, gunakan **Buka kunci log masuk** pada halaman butiran **Pengguna** (sebab diwajibkan, kebenaran `Sunting pengguna`). Apabila panel pentadbiran tidak dapat digunakan, pengendali IT menggunakan `uv run manage.py security_unlock_user`.

## Log masuk institusi (SSO)

Mendaftarkan log masuk OpenID Connect institusi (contohnya Microsoft Entra ID, Google Workspace, Keycloak) menambah butang "Log masuk dengan ..." pada skrin log masuk.

| Medan | Keterangan |
|---|---|
| Kunci | Pengecam huruf kecil, contohnya `school`. Menukarnya akan memutuskan pautan sedia ada |
| Label butang | Nama yang dipaparkan pada skrin log masuk |
| URL pengeluar | Pengeluar (issuer) penyedia. `/.well-known/openid-configuration` mesti tersedia di bawah alamat ini |
| ID klien, Rahsia klien | Nilai yang diterima semasa mendaftarkan aplikasi dengan penyedia. Rahsia disimpan dalam bentuk tersulit |
| Skop | Lalai `openid email profile` |
| Dikira sebagai pengesahan dua faktor | Hidupkan hanya apabila log masuk institusi itu sendiri mewajibkan pengesahan dua faktor. Apabila hidup, log masuk ini tidak diminta pengesahan dua faktor sekali lagi di sini |
| URI ubah hala untuk didaftarkan dengan penyedia | Daftarkan alamat yang dipaparkan pada skrin (`https://<server>/auth/sso/<key>/callback/`) tepat seperti adanya dalam tetapan aplikasi penyedia |

### Pemautan akaun

| Mod | Tingkah laku |
|---|---|
| Pengguna memautkan akaun mereka sendiri | Pengguna log masuk dengan kata laluan mereka dan menekan **Pautkan** di bawah **Keselamatan > Log masuk institusi** dalam portal (pengesahan kata laluan diwajibkan) |
| Pautkan secara automatik melalui e-mel institusi yang disahkan | Apabila e-mel yang disahkan oleh penyedia sepadan dengan e-mel institusi pada rekod pelajar, akaun dipautkan secara automatik pada log masuk pertama |

- Log masuk dengan akaun institusi yang belum dipautkan memaparkan notis supaya log masuk dengan kata laluan dan memautkannya. Akaun institusi sahaja tidak pernah mencipta akaun baharu.
- Pemautan dan nyahpautan direkodkan dalam log keselamatan.

### Membenarkan log masuk dengan kata laluan

Mematikan **Benarkan kata laluan bagi pengguna log masuk institusi** bermakna pengguna yang telah dipautkan hanya boleh menggunakan log masuk institusi. Oleh kerana akaun institusi sering hilang selepas pengijazahan, kami mengesyorkan supaya tetapan ini dibiarkan hidup dan pelajar yang hampir bergraduat diminta menyediakan e-mel peribadi dan kata laluan. Graduan terus log masuk dengan e-mel log masuk akaun (e-mel peribadi) dan kata laluan.
