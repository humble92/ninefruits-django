# 5. Tetapan institusi dan urutan persediaan awal

## Tetapan institusi

Ditetapkan di bawah **Tetapan > Institusi** (kebenaran `Urus tetapan institusi`).

| Tetapan | Penerangan |
|---|---|
| Nama institusi | Dimasukkan mengikut bahasa. Dipaparkan di penjuru kiri atas panel pentadbiran |
| Zon waktu | Rujukan untuk menentukan tarikh semester dan tempoh urusan, contohnya `Asia/Seoul`. Setiap masa yang disimpan dipaparkan dalam zon waktu ini |
| Bahasa yang ditawarkan | Bahasa yang boleh dipilih oleh pengguna. Hanya bahasa yang fail terjemahannya telah dipasang muncul dalam senarai |
| Bahasa lalai | Digunakan bagi pengguna yang belum memilih bahasa dan apabila bahasa pelayar tidak diketahui |

## Urutan persediaan awal bagi universiti baharu

Selepas pengendali IT selesai menjalankan `setup_install` (manual operasi, [Pemasangan](../operations/installation.md)), pentadbir urusan memasukkan data mengikut urutan di bawah. Langkah kemudian merujuk kod daripada langkah terdahulu, jadi patuhi urutan ini.

1. **Tetapan institusi**: nama, zon waktu, bahasa (bab ini)
2. **Data kod**: nilai etnik, jenis kemasukan dan jenis bilik ([bab 6](06-code-data.md)). Jika profil universiti Korea telah digunakan semasa pemasangan, jenis bilik sudah wujud.
3. Semak **Jenis unit organisasi**, kemudian **Unit organisasi**: universiti → fakulti → jabatan ([bab 7](07-org-units-and-programs.md)). Untuk unit yang banyak, gunakan CSV ([bab 9](09-csv-import.md)).
4. **Program**: program ijazah bagi setiap jabatan ([bab 7](07-org-units-and-programs.md))
5. **Bangunan**, **Bilik** ([bab 8](08-facilities.md), boleh menggunakan CSV)
6. Semak **Jenis semester** dan **Slot masa** ([bab 10](10-terms.md))
7. Semak **Kategori kursus** dan **Skala gred**. Satu skala lalai mesti ditetapkan ([bab 11](11-course-categories-and-grade-scales.md))
8. **Tahun akademik** → **Semester** → **Tempoh urusan** bagi setiap semester ([bab 10](10-terms.md))
9. **Pengguna dan akses**: peranan yang memerlukan skop unit organisasi, seperti pembantu jabatan, kini boleh memilih jabatan sebagai sasaran skop ([bab 2](02-users-and-roles.md))

Apabila data telah dimasukkan, minta pengendali IT menyemak tempoh urusan dengan `uv run manage.py term_inspect`.
