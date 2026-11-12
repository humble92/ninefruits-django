# 8. Bangunan dan bilik

Menu: **Data rujukan > Bangunan**, **Bilik** (kebenaran `Urus bangunan dan bilik`)

## Bangunan

Masukkan kod (contohnya `SCI`), nama (mengikut bahasa) dan alamat. Bangunan yang mempunyai bilik tidak boleh dipadamkan, jadi matikan **Aktif** apabila bangunan itu tidak lagi digunakan.

## Bilik

| Medan | Penerangan |
|---|---|
| Bangunan, Nombor bilik | Nombor bilik adalah unik dalam sesebuah bangunan, contohnya `101` |
| Nama | Pilihan, contohnya Auditorium Utama |
| Jenis bilik | Nilai daripada senarai kod `room_type` (bilik kuliah, makmal, dsb.) |
| Unit organisasi | Jabatan yang mengurus bilik itu (pilihan) |
| Kapasiti | Dibandingkan dengan kapasiti seksyen semasa jadual waktu disediakan ([bab 18](18-sections-and-timetables.md)) |
| Digunakan untuk jadual waktu | Apabila dimatikan, bilik itu dikecualikan semasa jadual waktu disediakan (pejabat, stor, dsb.) |

Untuk bilik yang banyak, gunakan [import CSV](09-csv-import.md). Bangunan mesti didaftarkan terlebih dahulu.
