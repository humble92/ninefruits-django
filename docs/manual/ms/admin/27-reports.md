# 27. Laporan dan Paparan reporting

Menu: **Laporan > Laporan** (kebenaran `Lihat dan muat turun laporan standard`). Lalai peranan: Pegawai Pendaftar, Pegawai Hal Ehwal Akademik, Pembantu Jabatan (dalam skop).

## Laporan standard

Pilih laporan dan penapisnya: sehingga 500 baris dipaparkan pada skrin, dan **Muat turun CSV** mendapatkan kesemuanya (UTF-8 dengan BOM, terus dibuka dalam Excel). Muat turun direkodkan dalam peristiwa audit `reports.exported` dan peristiwa log keselamatan `data.exported` (laporan, penapis, bilangan baris). Nilai yang bermula dengan `=`, `+`, `-`, `@` (atau tab atau pemisah baris) dieksport dengan tanda petik tunggal (`'`) di hadapan supaya Excel tidak menjalankannya sebagai formula.

| Laporan | Penapis | Kandungan |
|---|---|---|
| Senarai pelajar | Unit organisasi (termasuk unit di bawahnya), status, tahun pengajian | Nombor matrik, nama, program, unit organisasi, tahun pengajian, status, tarikh kemasukan, tarikh bergraduat, nombor ijazah |
| Bilangan pelajar mengikut unit, program, tahun dan status | Unit organisasi, status | Bilangan pelajar |
| Ringkasan gred semester | Semester, kedudukan akademik | Kredit dan PNG semester serta kumulatif, bilangan amaran akademik, kedudukan Senarai Dekan ([bab 21](21-grades.md)) |
| Calon bergraduat | Dipenuhi atau tidak | Semakan bergraduat terkini bagi setiap pelajar dan program ([bab 26](26-graduation.md)) |
| Perubahan status | Semester, tempoh | Jenis perubahan, status sebelum dan selepas, tarikh berkuat kuasa, status permohonan |
| Pendaftaran mengikut seksyen | Semester, unit organisasi | Seksyen, pensyarah, kapasiti, berdaftar, menunggu |
| Pelajar yang tidak mendaftar dalam semester | Semester, unit organisasi | Pelajar yang sedang belajar tanpa pendaftaran kursus dalam semester tersebut |

Apa yang boleh dilihat mengikut skop kebenaran pelihat (skop paparan rekod pelajar dan seumpamanya). Laporan yuran dan yuran pengajian sistem lama (YUSTIC) (yuran pengajian belum dibayar dan seumpamanya) berada di luar skop dan tidak wujud.

## Paparan reporting

Laporan membaca paparan (view) skema `reporting` dalam pangkalan data. Alat BI dan pengguna SQL membuat pertanyaan pada paparan yang sama dengan peranan baca sahaja `app_reporting`.

| Paparan | Kandungan |
|---|---|
| `reporting.students` | Rekod pelajar + nama individu + nama program dan unit organisasi |
| `reporting.headcount` | Bilangan pelajar mengikut unit organisasi, program, tahun pengajian dan status |
| `reporting.term_records` | Ringkasan gred bagi setiap semester |
| `reporting.course_grades` | Gred bagi setiap kursus (muktamad atau tidak, gred, lulus, ulang kursus) |
| `reporting.section_enrollments` | Berdaftar dan menunggu bagi setiap seksyen, pensyarah |
| `reporting.section_meetings` | Waktu kelas dan bilik |
| `reporting.status_changes` | Perubahan status |
| `reporting.degree_audits` | Semakan bergraduat terkini bagi setiap pelajar dan peranan program |

- Lajur yang diterjemahkan (`program_name` dan seumpamanya) mengikut locale sesi: `SET app.locale = 'ko';`. Lajur jsonb mentah (`program_name_i18n` dan seumpamanya) juga tersedia.
- Paparan ini ialah `security_invoker`, jadi keselamatan peringkat baris (row level security) pelihat terpakai tanpa perubahan. Apabila dibaca dengan akaun pelajar, ia hanya mengembalikan baris pelajar tersebut.
- Takrifan paparan berada dalam `db/sql/views/reporting.sql` (`database/sql/views/reporting.sql` asal tanpa perubahan); selepas perubahan, ia digunakan semula daripada migrasi `core`. Aplikasi membacanya melalui model tidak terurus (`ninefruits.reporting.models`, cth. `ReportStudent`).

Paparan `AV_*` sistem lama (kira-kira 90 kesemuanya) tidak digunakan dan tidak dipindahkan.

## Skrin dalam pemasangan ini

- **Laporan > Laporan** (`/admin/reports/`): pilih laporan dan tekan **Papar** untuk memaparkan penapisnya (sistem asal menukarnya sebaik sahaja laporan dipilih). Isikan penapis dan tekan **Papar** sekali lagi. Laporan yang mempunyai penapis semester tiada baris sehingga semester dipilih.
- Alamat CSV ialah `/reports/{report}.csv?filter=value` (cth. `/reports/students.csv?status=enrolled`). Hanya nama laporan dan penapis yang disenaraikan diterima, dan lajur serta susunannya ditetapkan oleh takrifan laporan.
- Masa dalam CSV (diaudit, diputuskan) ditulis seperti sistem asal, sebagai teks PostgreSQL dalam UTC (`2026-10-24 07:26:59+00`); tarikh ialah `YYYY-MM-DD`, benar/palsu `Y`/`N`.
- Penapis unit bagi Pendaftaran mengikut seksyen menapis mengikut kod unit (paparan tiada id unit). Dalam sistem asal, memilih penapis ini gagal.
- Seksyen dan waktu kelas tiada keselamatan peringkat baris, jadi setiap baris seksyen dipaparkan. Bilangan berdaftar dan menunggu hanya mengira pendaftaran kursus dan entri senarai menunggu yang boleh dilihat oleh pembaca.

[Kandungan manual pentadbir](README.md)
