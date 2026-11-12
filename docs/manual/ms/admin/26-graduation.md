# 26. Semakan Bergraduat dan Pengijazahan

Menu: **Pengijazahan > Semakan bergraduat**, butang **Semakan bergraduat** pada skrin paparan rekod pelajar, **Tetapan > Tetapan pengijazahan** (corak nombor ijazah, PNGK minimum; kebenaran `Proses pengijazahan, berikan pengecualian syarat`). Pelajar melihat kemajuan mereka sendiri dalam portal di bawah **Syarat bergraduat**.

| Kebenaran | Apa yang dibenarkan |
|---|---|
| `Jalankan dan lihat semakan bergraduat` | Menjalankan semakan (tunggal dan pukal) dan melihat semakan yang disimpan |
| `Proses pengijazahan, berikan pengecualian syarat` | Memproses pengijazahan (pukal), pengecualian syarat |

Lalai peranan: Pegawai Pendaftar mempunyai kedua-duanya, Pegawai Hal Ehwal Akademik mempunyai kebenaran semakan.

## Perbezaan daripada sistem lama

- **Syarat disemak.** Helaian semakan bergraduat sistem lama (YUSTIC) hanya mencetak kredit dan PNG bagi setiap kategori kursus dan tidak membandingkannya dengan apa-apa (kotak hasil semakan kosong). Sistem baharu membandingkan dengan **syarat bergraduat** bagi setiap tahun kurikulum ([bab 17](17-courses-and-curriculum.md)) dan melaporkan sama ada setiap syarat dipenuhi.
- **Semakan diwajibkan sebelum pengijazahan.** Dalam sistem lama, memasukkan kod perubahan status Z sudah memadai. Sistem baharu memproses pengijazahan hanya apabila semakan terkini yang disimpan dipenuhi.
- **Sistem mengeluarkan nombor ijazah.** Sistem lama tidak menggunakan medan nombor ijazah dan nombor diploma ditulis dengan tangan.
- Graduan tidak dipindahkan ke jadual lain. Hanya status pelajar berubah kepada `Bergraduat` dan akaun mengekalkan akses alumni ([bab 13](13-status-changes-and-advisors.md)).

## Peraturan semakan

Set syarat bagi **program utama × tahun kurikulum** pelajar dicari dan setiap syarat disemak.

| Jenis syarat | Semakan |
|---|---|
| Kredit dalam kategori | Jumlah kredit kursus yang lulus yang kategorinya ialah kategori tersebut **atau kategori di bawahnya** ≥ kredit minimum |
| Kursus wajib | Setiap kursus dalam senarai telah lulus. **Kursus setara** yang berkuat kuasa pada masa pendaftaran dikira |
| Pilihan daripada kursus | Kredit atau bilangan kursus yang lulus daripada senarai (termasuk kursus setara) pada atau melebihi ambang |
| Lulus peperiksaan | Keputusan lulus bagi jenis peperiksaan tersebut wujud ([bab 24](24-assessments.md)) |

- "Lulus" bermaksud pendaftaran yang gred muktamadnya ialah gred lulus (`is_passed`). Kursus yang lulus pada rekod pelajar lain bagi individu yang sama (sebelum kemasukan semula) juga dikira.
- **Jumlah kredit** set syarat dan **PNGK minimum** dalam **Tetapan > Tetapan pengijazahan** (lalai 2.0; kosong: tidak digunakan) turut disemak.
- Major kedua dan minor disemak secara berasingan berbanding set syarat masing-masing dan dipaparkan bersama. Syarat untuk bergraduat ialah program utama dipenuhi.
- Tanpa set syarat yang sepadan dengan tahun kurikulum, semakan tidak dipenuhi (set tersebut mesti dicipta).

## Semakan

- **Semak sekarang**: butang **Semakan bergraduat** pada skrin paparan rekod pelajar. Ia menyemak data semasa serta-merta dan memaparkan kursus yang lulus dan yang belum bagi setiap syarat. **Simpan semakan ini** menyimpannya.
- **Semakan pukal**: **Semakan bergraduat > Jalankan semakan** (semester, mulai tahun pengajian) atau arahan `uv run manage.py degree_audit_run --term={term} --min-year-level=4 --actor=...` ([arahan operasi](../operations/commands.md)). Semakan disimpan bagi setiap pelajar yang sedang belajar.
- Semakan yang disimpan ialah **gambaran (snapshot)**. Pindaan gred kemudian tidak mengubahnya; menyemak semula menambah gambaran baharu. Senarai hanya memaparkan semakan **terkini** bagi setiap pelajar dan peranan program, dan pemprosesan pengijazahan juga melihat semakan terkini.

## Pengecualian

Satu syarat dikecualikan bagi keadaan individu seperti pertukaran major, kemasukan pindahan atau program pertukaran. Dua orang terlibat (keputusan 2026-10-23).

1. **Permohonan**: di bawah **Kecualikan syarat** pada skrin paparan rekod pelajar, pilih syarat dan nyatakan sebab (kebenaran `Proses pengijazahan, berikan pengecualian syarat`). Peristiwa audit `graduation.waiver_requested`.
2. **Luluskan atau tolak**: di bawah **Pengijazahan > Pengecualian syarat**, **kakitangan lain** yang mempunyai kebenaran yang sama meluluskan (catatan pilihan) atau menolak (catatan diwajibkan). Tiada sesiapa boleh memutuskan permohonannya sendiri. Peristiwa audit `graduation.waiver_approved`/`waiver_rejected`.
3. Hanya pengecualian yang diluluskan dikira sebagai dipenuhi dalam semakan. Satu pengecualian menunggu atau diluluskan bagi setiap syarat.
4. **Tarik balik**: **Tarik balik pengecualian** pada pengecualian yang diluluskan (sebab diwajibkan) menghentikan penggunaannya dan mengekalkan sejarah (status `Ditarik balik`, peristiwa audit `graduation.waiver_lifted`). Pengijazahan pelajar yang telah diproses tidak dibatalkan.

Setiap langkah juga muncul dalam rekod perubahan data.

## Memproses pengijazahan

Dalam senarai **Semakan bergraduat**, pilih pelajar dan klik **Luluskan bergraduat** (tarikh bergraduat, sebab). Bagi setiap pelajar:

1. Menyemak bahawa pelajar sedang belajar dan semakan program utama terkini dipenuhi. Jika tidak, pelajar tersebut dilangkau dan sebabnya dilaporkan.
2. Merekod perubahan status `Bergraduat` (status `Bergraduat`, tarikh bergraduat). Ia muncul dalam sejarah perubahan status [bab 13](13-status-changes-and-advisors.md).
3. Mengeluarkan nombor ijazah. Coraknya ialah `{PROGRAM}-{YYYY}-{SEQ:5}` dalam **Tetapan > Tetapan pengijazahan** (lalai, cth. `CS-2026-00001`; token `{PROGRAM}` kod program, `{YYYY}`, `{YY}` tahun bergraduat, `{SEQ:n}` nombor urutan bagi setiap awalan). Pemprosesan serentak tidak pernah bertembung.
4. Peristiwa audit `graduation.processed` (nombor matrik, tarikh bergraduat, nombor ijazah, semakan yang menjadi asasnya).

Graduan terus melihat gred dan sijil mereka dalam portal, dan surat pengesahan tamat pengajian mencetak tarikh bergraduat dan nombor ijazah ([bab 23](23-certificates.md)). Pengijazahan yang salah dibetulkan dengan perubahan status (kemasukan semula dan seumpamanya). Tiada fungsi untuk membatalkan pengijazahan.

## Soalan lazim

- **Semakan menyatakan "tiada set syarat".** Program tersebut tiada set syarat bergraduat yang meliputi tahun kurikulum pelajar. Cipta satu seperti dalam [bab 17](17-courses-and-curriculum.md).
- **Kursus setara tidak diiktiraf.** Tempoh berkuat kuasa kesetaraan mesti merangkumi tarikh mula semester ketika kursus itu diambil.
- **Apa yang berlaku apabila saya menukar corak nombor ijazah?** Ia terpakai mulai pengeluaran seterusnya. Apabila awalan berubah, nombor urutan bermula semula pada 1.

## Skrin dalam pemasangan ini

Skrin dan fungsinya adalah sama seperti sistem asal (Filament, Livewire); sesetengah kawalan berfungsi sedikit berbeza.

- Senarai **Pengijazahan > Semakan bergraduat** (`/admin/graduation/degreeaudit/`): penapis secara lalai ialah peranan program **Program utama** dan status pelajar **Aktif**. **Buka** pada sesuatu baris memaparkan semakan yang disimpan; **Semak semula** membuka halaman pengesahan. **Jalankan semakan** ialah butang tindakan di atas senarai (semester, mulai tahun pengajian, lalai 4).
- Untuk **Luluskan bergraduat**, tandakan baris, pilih **Luluskan bergraduat** dalam senarai tindakan dan jalankannya: satu halaman meminta tarikh bergraduat dan sebab. Pelajar yang tidak dapat diproses disenaraikan bersama nombor matrik dan sebabnya sebagai amaran (sehingga 10).
- **Semakan bergraduat** pada rekod pelajar memaparkan semakan yang dinilai sekarang pada halamannya sendiri; **Simpan semakan ini** di bawahnya menyimpan semakan tersebut. **Kecualikan syarat** membuka halaman untuk memilih syarat dan menyatakan sebab.
- **Pengijazahan > Pengecualian syarat** (`/admin/graduation/degreerequirementwaiver/`): penapis status secara lalai ialah **Menunggu** dan menu memaparkan bilangan yang menunggu. **Luluskan**, **Tolak** dan **Tarik balik pengecualian** pada sesuatu baris membuka halaman untuk catatan (sebab). Membukanya bagi permohonan sendiri atau bagi pengecualian yang telah diputuskan mengembalikan 403.
- **Tetapan > Tetapan pengijazahan** (`/admin/settings/graduation/`): corak nombor ijazah hanya disimpan dengan tepat satu `{SEQ:n}`. PNGK minimum ialah 0 hingga 5; kosong bermakna tidak digunakan.
- **Syarat bergraduat** portal (`/portal/graduation/`): dalam menu pelajar dan alumni. Dengan beberapa rekod pelajar (kemasukan semula), ia menggunakan rekod yang dipilih dalam portal.
- Pengijazahan menulis perubahan status dan nombor ijazah dalam konteks sistem selepas menyemak kebenaran (pemprosesan pengijazahan, skop rekod, skop kelulusan perubahan status), jadi kakitangan pengijazahan tidak memerlukan `Cipta dan sunting rekod pelajar` juga. Rekod perubahan data masih menamakan pengguna yang memprosesnya.

[Kandungan manual pentadbir](README.md)
