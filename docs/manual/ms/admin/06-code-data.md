# 6. Data kod, negara, bahasa

Menu: **Data rujukan > Senarai kod**, **Negara**, **Bahasa** (kebenaran `Urus data kod, negara dan bahasa`)

## Data kod

Senarai pendek yang berbeza antara satu universiti dengan universiti lain. Setiap senarai (jenis) mempunyai nilai kod.

| Kod senarai | Kegunaan | Sistem lama (YUSTIC) |
|---|---|---|
| `ethnicity` | Etnik | `FNATION` |
| `admission_type` | Jenis kemasukan | `FADMDIST` |
| `room_type` | Jenis bilik | `ROOM.FORWHAT` |

- Senarai sistem (tiga di atas) dicari mengikut kod dalam aplikasi, jadi kod senarainya tidak boleh ditukar atau dipadamkan. Nilai boleh ditambah dengan bebas.
- Buka sesuatu senarai dan tambah nilai di bawah **Kod** di bahagian bawah. Kod menggunakan huruf kecil, digit dan garis bawah (contohnya `korean`). Masukkan nama mengikut bahasa; nama dalam bahasa Inggeris wajib diisi.
- Jangan padamkan nilai yang tidak lagi digunakan; matikan **Aktif** sebaliknya. Nilai tidak boleh dipadamkan selagi masih ada data yang menggunakannya.
- Masukkan nilai yang banyak dengan [import CSV](09-csv-import.md).

## Negara dan bahasa

Senarai standard ISO (249 negara, kira-kira 180 bahasa) dimuatkan semasa pemasangan. Nama diisi secara automatik bagi bahasa yang dipasang.

- Untuk menukar nama yang dipaparkan pada skrin, tukar di bawah **Sunting**. Nama yang ditukar dikekalkan walaupun selepas kemas kini sistem.
- Untuk menyembunyikan sesuatu entri daripada senarai pilihan, matikan **Aktif**.
