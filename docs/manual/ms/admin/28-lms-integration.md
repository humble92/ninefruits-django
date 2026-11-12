# 28. Integrasi LMS

Menu: panel pentadbiran **Integrasi LMS > Platform LMS**, **Pautan kursus**, **Log penyegerakan** (kebenaran `Urus platform LMS, pautan dan penyegerakan`; lalai: Pentadbir Sistem, Pegawai Hal Ehwal Akademik). Pensyarah menggunakan pautan LMS di bawah **Pengajaran saya** dalam portal dan dalam butiran seksyen, serta **Muatkan markah daripada LMS** pada skrin kemasukan gred. Pemuatan mengikut syarat yang sama seperti kemasukan gred (pensyarah yang ditetapkan, dalam tempoh kemasukan gred).

Butiran untuk pembangun (menulis penyambung, API) terdapat dalam [panduan integrasi LMS](../../../lms-integration-guide.md).

## Apa yang pergi ke mana

| SIS → LMS | Bila |
|---|---|
| Seksyen (penciptaan kursus) + pensyarah | Apabila seksyen **diterbitkan**, dan dengan `lms_sync` |
| Pendaftaran yang disahkan → pendaftaran dalam LMS | Serta-merta semasa pendaftaran kursus, kenaikan senarai menunggu atau pendaftaran oleh kakitangan |
| Gugur atau tarik diri → nyahdaftar | Serta-merta |
| Penyelarasan penuh | Setiap hari pada 02:30 (`lms_reconcile`, tugas berjadual `lms.reconcile`) |

| LMS → SIS | Bila |
|---|---|
| Markah akhir (draf) | Apabila pensyarah mengklik **Muatkan markah daripada LMS** pada skrin kemasukan gred. Penyimpanan dan penghantaran dilakukan oleh pensyarah |

Gred muktamad tidak dihantar ke LMS. Bahan kursus, tugasan dan kuiz berada dalam LMS.

## Platform

**Platform LMS**: kod, nama (bagi setiap bahasa), pemacu, URL asas, kelayakan akses, aktif, segerakkan senarai pelajar, tarik markah akhir.

- Pemacu **Tiada (rekod sahaja)**: tidak memanggil apa-apa dan merekod apa yang akan dihantar. Gunakannya untuk menyemak aliran atau untuk demonstrasi sebelum integrasi. Platform `DEMO` dalam data demo menggunakannya.
- `Moodle`, `Open edX`: belum ada penyambung (ditandakan "belum dilaksanakan"). Apabila dipilih, penyegerakan direkodkan sebagai gagal.
- Menghidupkan **Aktif** menjadikan penerbitan seksyen dan perubahan pendaftaran mengalir serta-merta mulai saat itu dan memasukkan platform ke dalam penyelarasan setiap malam.
- **Kelayakan akses** ditulis satu `key=value` bagi setiap baris (cth. `token=...`). Ia disimpan dalam bentuk tersulit dan tidak pernah dipaparkan semula. Membiarkan medan kosong semasa suntingan mengekalkan nilai yang disimpan. Sejarah perubahan data juga tidak menyimpan nilai tersebut.

## Pautan kursus dan log penyegerakan

- **Pautan kursus**: seksyen mana dipautkan kepada kursus platform mana (id, URL), status (Menunggu/Dipautkan/Gagal), penyegerakan terakhir dan ralat. Penapis bagi platform, status dan semester; cari mengikut kod kursus. Tindakan baris **Segerakkan semula** (dengan halaman pengesahan) menolak seksyen, pensyarah dan senarai pelajar sekali lagi.
- **Log penyegerakan**: hasil dan mesej bagi setiap langkah (kursus, tambah dan buang ahli, tarik markah, markah diterima, penyelarasan). Lihat di sini untuk punca kegagalan. Membuka sesuatu baris memaparkan masa mula dan tamat serta muatan (payload).
- Arahan: `uv run manage.py lms_sync {platform} --term={term}` (tolakan penuh, `--dry-run`), `uv run manage.py lms_reconcile` (penyelarasan). Lihat [arahan operasi](../operations/commands.md#integrasi-lms-fasa-12).

## Portal

- Pautan kursus platform dipaparkan dalam butiran kursus bagi pelajar dan pensyarah serta dalam senarai **Pengajaran saya** pensyarah (lajur **LMS**; seksyen yang dipautkan sahaja).
- Kemasukan gred: apabila **Tarik markah akhir** dihidupkan bagi platform dan seksyen telah dipautkan, butang **Muatkan markah daripada LMS** muncul. Ia hanya mengisi lajur markah dan tidak menyimpan.

## API integrasi

Satu API (`/api/v1/lms/platforms/...`) melayani platform yang melaporkan hasil kemudian atau menghantar markah mereka sendiri. Cipta akaun integrasi yang berasingan dengan hanya kebenaran `Urus platform LMS, pautan dan penyegerakan`; pengendali mengeluarkan tokennya dengan `uv run manage.py api_issue_token {email} --days=365` dan menyerahkannya kepada pentadbir platform. Token hanya dipaparkan sekali, semasa ia dikeluarkan. `api_revoke_tokens` membatalkannya. Pengeluaran dan pembatalan direkodkan dalam log audit.

- Markah yang diterima melalui penghantaran markah (`.../scores/`) juga tidak disimpan. Apabila pensyarah mengklik **Muatkan markah daripada LMS**, markah terkini yang diterima mengisi borang sebagai draf.
- Hasil penyegerakan (`.../sync-results/`) disimpan dalam **Log penyegerakan**, dan hasil kursus menukar status dalam **Pautan kursus**.

## Soalan lazim

- **Seorang pelajar tiada dalam LMS.** Pelajar memerlukan akaun (pengguna) untuk disegerakkan. Jika tiada, jemput mereka ([bab 14](14-merge-and-invitations.md)); penyelarasan seterusnya akan menambah mereka.
- **Penyegerakan kekal gagal.** Baca mesej dalam log penyegerakan. Kelayakan akses yang telah luput adalah perkara biasa. Ubah nilai pada skrin suntingan platform dan **Segerakkan semula**.
- **Kami telah menukar platform.** Cipta platform baharu dan matikan Aktif bagi platform lama. Pautan dicipta secara berasingan bagi setiap platform.

## Skrin dalam pemasangan ini

Skrin dan cirinya adalah sama seperti sistem asal (Filament, Livewire); sesetengah interaksi berbeza.

- Kelayakan akses dimasukkan sebagai baris `key=value` dalam medan teks, menggantikan jadual kunci/nilai sistem asal. Baris yang tidak sah ditolak bersama nombor barisnya.
- **Pilihan** platform (id peranan bagi setiap platform dan seumpamanya) tiada medan pada skrin. Pembangun menetapkannya apabila penyambung memerlukannya ([panduan integrasi](../../../lms-integration-guide.md) bahagian 3).
- **Segerakkan semula** melalui halaman pengesahan. Ralat penyambung (pemacu tanpa penyambung, gangguan platform) dipaparkan sebagai mesej "Penyegerakan gagal: ..." dan pautan kursus menjadi Gagal (sistem asal memaparkan halaman ralat).
- Log penyegerakan hanya boleh dibaca. Membuka sesuatu baris memaparkan muatan sebagai JSON.
- **Muatkan markah daripada LMS** pada skrin kemasukan gred berada dalam baris butang di bawah jadual. Ia memaparkan halaman sekali lagi dengan hanya medan markah diubah, mengekalkan apa yang telah ditaip. Tiada apa-apa disimpan sehingga **Simpan draf**.
- API integrasi dan arahan token (`api_issue_token`, `api_revoke_tokens`) adalah baharu dalam pemasangan ini (sistem asal tiada API).

[Kandungan manual pentadbir](README.md)
