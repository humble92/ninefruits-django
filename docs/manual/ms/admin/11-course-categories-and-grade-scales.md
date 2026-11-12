# 11. Kategori kursus dan skala gred

## Kategori kursus

Menu: **Data rujukan > Kategori kursus** (kebenaran `Urus kategori kursus`). Menggantikan `SFOBJDIST` dalam sistem lama (YUSTIC).

Pengelasan kursus, seperti wajib pendidikan umum atau elektif major. Kategori boleh dikumpulkan dengan menetapkan **Induk** (contohnya Pendidikan umum → Wajib pendidikan umum, Elektif pendidikan umum). Syarat bergraduat ([bab 17](17-courses-and-curriculum.md), [bab 26](26-graduation.md)) merujuk kategori ini, contohnya "30 kredit kursus wajib major".

## Skala gred

Menu: **Data rujukan > Skala gred** (kebenaran `Urus skala gred`). Menggantikan `SSCOREDEF` dalam sistem lama.

| Medan skala | Penerangan |
|---|---|
| Nilai gred maksimum | Contohnya 4.5 |
| Lalai | Hanya satu skala boleh menjadi lalai. Ia hanya boleh dihidupkan selagi tiada skala yang menjadi lalai (lihat di bawah) |

Buka sesuatu skala dan tambah gred di bawah **Gred** di bahagian bawah.

| Medan gred | Penerangan |
|---|---|
| Gred | Contohnya `A+`, `P` |
| Nilai gred | Wajib bagi gred yang dikira dalam PNG |
| Dari (%), Hingga (%) | Julat penukaran markah mentah (pilihan), contohnya A+ 95–100 |
| Dikira dalam PNG | Matikan bagi gred yang dikecualikan daripada PNG, seperti P/NP |
| Lulus | Matikan bagi gred yang tidak memperoleh kredit, seperti F atau NP |
| Untuk | Kursus bergred (gred huruf), kursus lulus/gagal (P, NP) atau Kedua-duanya (contohnya I, tidak lengkap). Skrin kemasukan gred hanya memaparkan gred yang sepadan dengan asas penggredan kursus |

**Skala lalai ditetapkan semasa pemasangan dan tidak boleh ditukar** (keputusan 2026-10-23), kerana setiap gred dan PNG dinyatakan dalam skala tersebut. Tetapkannya dengan `setup_install --grade-scale=4.5|4.3`; tanpa pilihan ini, skala profil pertama menjadi lalai. Bendera lalai tidak boleh ditukar pada skrin dan skala lalai tidak boleh dipadamkan. Julat markah dan nilai gred bagi setiap gred disunting pada skrin ini ([bab 21](21-grades.md)).

Skala yang dimuatkan oleh profil

- Universiti Korea: skala 4.5 (`KR45`): A+ 4.5 (95–100), A0 4.0 (90–), B+ 3.5 (85–), B0 3.0 (80–), C+ 2.5 (75–), C0 2.0 (70–), D+ 1.5 (65–), D0 1.0 (60–), F 0, P, NP
- `--grade-scale=4.3` atau profil YUST lama: skala 4.3 (`KR43` atau `YUST43`): A+ 4.3 (97–100), A0 4.0 (93–), A- 3.7 (90–), B+ 3.3 (87–), B0 3.0 (83–), B- 2.7 (80–), C+ 2.3 (77–), C0 2.0 (73–), C- 1.7 (70–), D+ 1.3 (67–), D0 1.0 (63–), D- 0.7 (60–), F 0, P, NP (profil lama turut merangkumi N dan I). Julat markah bermula dengan selang 3 mata, jadi laraskannya mengikut standard institusi.

Skala yang telah digunakan dalam gred tidak boleh dipadamkan.
