# 20. Pendaftaran Kursus

Menu: **Pendaftaran kursus > Pendaftaran kursus**, **Sekatan**, **Kelulusan khas**, **Peraturan pendaftaran**, **Had kredit**, **Cubaan pendaftaran**, serta tab **Senarai pelajar** dan **Senarai menunggu** pada skrin suntingan **Kurikulum dan seksyen > Seksyen**

| Kebenaran | Apa yang dibenarkan |
|---|---|
| `Lihat pendaftaran kursus dan senarai pelajar` | Melihat pendaftaran kursus, senarai pelajar dan cubaan pendaftaran |
| `Daftar, gugur dan tarik diri kursus bagi pihak pelajar (dengan sebab)` | Pendaftaran oleh kakitangan, menggugurkan dan menarik diri, mengeluarkan daripada senarai menunggu dan menaikkan serta-merta. Apabila ditetapkan dengan skop unit organisasi, hanya seksyen yang ditawarkan oleh unit tersebut |
| `Kenakan dan tarik balik sekatan, berikan kelulusan khas peraturan` | Sekatan, kelulusan khas. Apabila ditetapkan dengan skop, hanya pelajar dalam skop tersebut |
| `Urus set peraturan pendaftaran dan had kredit` | Set peraturan bagi setiap semester, had kredit |

Lalai peranan: Pegawai Pendaftar mempunyai keempat-empat kebenaran, Pegawai Hal Ehwal Akademik mempunyai kebenaran melihat serta peraturan dan had kredit, Pembantu Jabatan mempunyai kebenaran melihat dan pelarasan pendaftaran (ditetapkan dengan skop jabatan).

Senarai hanya memaparkan pelajar yang rekodnya boleh anda lihat dan pendaftaran kursus bagi seksyen dalam skop anda. Keselamatan peringkat baris (row level security) dalam pangkalan data menguatkuasakan skop yang sama.

## Perbezaan daripada sistem lama

- Peraturan yang dikodkan secara tetap berdasarkan digit nombor matrik atau kod jabatan dalam sistem lama (YUSTIC), seperti had kredit atau pengecualian kursus bank kredit, kini menjadi **tetapan bagi setiap semester**. Peraturan YUST lama dihasilkan semula oleh profil pemasangan `yust-legacy` (di bawah).
- Apabila permintaan ditolak, **setiap sebab dipaparkan serentak** (sistem lama berhenti pada sebab pertama). Setiap cubaan dan hasil bagi setiap peraturan disimpan dalam **Cubaan pendaftaran**.
- Pepijat had kredit sistem lama bagi fakulti kejururawatan dengan nombor matrik mulai 2014 (18 kredit dikenakan sedangkan sepatutnya 21) tidak dihasilkan semula. 21 kredit terpakai.
- Tiada kemasukan pembelian buku teks semasa pendaftaran kursus.

## Menyediakan semester

1. **Tempoh urusan** ([bab 10](10-terms.md)): troli pendaftaran, pendaftaran kursus (pembukaan berperingkat mengikut tahun pengajian), tambah/gugur, tarik diri. Tempoh tambah/gugur dan tarik diri ditetapkan bagi setiap sesi.
2. **Peraturan pendaftaran > Sediakan peraturan bagi semester**: pilih semester dan semester terdahulu untuk disalin. Biarkan kosong untuk bermula daripada nilai lalai. Semester tanpa set peraturan menggunakan nilai lalai.
3. **Had kredit**: had bagi setiap jenis semester dan kumpulan pelajar (di bawah).
4. **Seksyen**: kapasiti, tempat simpanan (tempat simpanan dan masa pembukaannya), **Saiz senarai menunggu** ([bab 18](18-sections-and-timetables.md)). Seksyen mesti **diterbitkan** untuk menerima pendaftaran.
5. **Sekatan**: masukkan senarai pelajar yang dikenakan sekatan, cth. yuran pengajian belum dibayar (import CSV boleh dilakukan, [bab 9](09-csv-import.md)).
6. Semak: `uv run manage.py registration_preflight 2027-SP` ([arahan operasi](../operations/commands.md)). Ia melaporkan tempoh urusan, set peraturan, kapasiti dan bilangan pelajar tanpa had kredit.

## Peraturan

Semua peraturan disemak mengikut susunan di bawah. **Tempoh, seksyen dibuka dan tempat duduk** sentiasa terpakai dan tidak terdapat dalam senarai.

| Peraturan | Apa yang disemak | Parameter |
|---|---|---|
| Tempoh pendaftaran | Tempoh urusan yang sepadan dengan kriteria sasaran pelajar mesti dibuka. Menggugurkan memerlukan tempoh pendaftaran atau tempoh tambah/gugur bagi sesi kursus tersebut; tarik diri memerlukan tempoh tarik diri bagi sesi tersebut | Tiada |
| Sekatan | Ditolak apabila sekatan menyekat pendaftaran | Tiada |
| Status pelajar | Hanya status pelajar yang dipilih (lalai: sedang belajar) boleh mendaftar | Status yang dibenarkan |
| Kelayakan seksyen | Kriteria kelayakan dan pengecualian seksyen | Tiada |
| Kursus sama dua kali | Sesuatu kursus hanya sekali bagi setiap semester | Tiada |
| Pertindihan masa | Ditolak apabila masa bertindih dengan seksyen lain yang didaftarkan. Separuh pertama dan separuh kedua semester dengan tarikh yang tidak bertindih tidak bercanggah | Pertindihan dibenarkan (minit) |
| Had kredit | Jumlah kredit yang didaftarkan ≤ had kredit yang terpakai. Kursus yang tetapan "Dikira dalam had kredit" dimatikan tidak dikira | Tiada (ditetapkan pada skrin Had kredit) |
| Prasyarat | Prasyarat telah lulus (kursus setara dikira, gred minimum); kosyarat boleh didaftarkan dalam semester yang sama | Tiada (ditetapkan pada skrin kursus) |
| Ulang kursus | Sama ada kursus yang telah lulus boleh diambil semula | Ulang kursus dibenarkan, percubaan maksimum, hanya di bawah gred |

Halaman set peraturan menyenaraikan peraturannya; **Sunting** pada sesuatu baris membuka halaman peraturan tersebut. Setiap peraturan mempunyai tetapan tersendiri.

- **Aktif**: apabila mati, peraturan tidak disemak.
- **Jika tidak dipenuhi**: Sekat atau Amaran sahaja. Dengan amaran, pendaftaran diteruskan dan pelajar hanya melihat mesej.
- **Kelulusan khas dibenarkan**: mesti hidup supaya kelulusan khas dan medan "Ketepikan peraturan" dalam pendaftaran oleh kakitangan berkuat kuasa. Ia mati secara lalai bagi sekatan dan kursus sama dua kali.
- Parameter hanya dipaparkan bagi peraturannya sendiri (status pelajar: status yang dibenarkan; pertindihan masa: pertindihan yang dibenarkan dalam minit; ulang kursus: ulang kursus dibenarkan, percubaan maksimum, di bawah gred). Nilai pilihan yang kosong bermaksud "tiada had".

Ulang kursus dikesan secara automatik dan pendaftaran ditandakan **Ulang kursus**. Cara ulang kursus dikira dalam PNG diterangkan dalam [bab 21](21-grades.md).

Apabila keluaran baharu menambah peraturan pada katalog, pemasangannya (`setup_install`) menambah peraturan itu beserta nilai lalainya pada set peraturan sedia ada. Tetapan yang telah diubah oleh pentadbir dikekalkan.

## Had kredit

Tetapkan jenis semester (kosong: setiap jenis semester), pelajar (tahun pengajian, tahun kemasukan, program, unit organisasi), kredit maksimum dan keutamaan. Apabila beberapa had sepadan dengan seseorang pelajar, hanya **had yang mempunyai keutamaan tertinggi** terpakai. Apabila tiada yang sepadan, tiada had (`registration_preflight` melaporkan perkara ini).

Contoh: peraturan YUST lama (profil `yust-legacy`)

| Jenis semester | Pelajar | Maksimum | Keutamaan |
|---|---|---|---|
| Semester 1 dan 2 | Kemasukan 2014 atau kemudian, fakulti kejururawatan (kod unit organisasi `NURS`) | 21 | 40 |
| Semester 1 dan 2 | Kemasukan 2014 atau kemudian | 18 | 30 |
| Semester 1 dan 2 | Kemasukan 2013 atau lebih awal, fakulti kejururawatan | 20 | 20 |
| Semester 1 dan 2 | Kemasukan 2013 atau lebih awal | 17 | 10 |
| Musim panas dan musim sejuk | Kemasukan 2014 atau kemudian, fakulti kejururawatan / lain-lain | 6 / 5 | 40 / 30 |
| Musim panas dan musim sejuk | Kemasukan 2013 atau lebih awal | 6 | 10 |

Bagi kursus bank kredit yang kodnya bermula dengan `009` atau `900`, matikan "Dikira dalam had kredit" pada kursus tersebut. Profil ini dipasang dengan `uv run manage.py setup_install --profile=yust-legacy` (ia termasuk profil universiti Korea). Menjalankannya sekali lagi membaiki had yang mempunyai nama yang sama.

## Tempat duduk dan senarai menunggu

- Tempat duduk dijamin pada saat pendaftaran dengan mengunci baris seksyen. Walaupun ramai pelajar mendaftar serentak, kapasiti tidak akan dilampaui.
- **Tempat simpanan** (cth. 30 tempat bagi pelajar major) hanya digunakan oleh pelajar berkenaan sehingga masa pembukaan. Tempat simpanan yang berbaki menjadi tempat terbuka pada masa pembukaan. Portal memaparkannya sebagai "terbuka, simpanan, jumlah".
- Apabila **Saiz senarai menunggu** lebih besar daripada 0, pelajar boleh **Sertai senarai menunggu** bagi seksyen yang penuh. Menyertai senarai menunggu juga memerlukan pelajar melepasi setiap peraturan kecuali tempat duduk.
- Apabila tempat duduk dibebaskan oleh pengguguran, tarik diri atau pelepasan tempat simpanan, pelajar yang menunggu **dinaikkan secara automatik** mengikut susunan (tugas latar belakang; satu kenaikan bagi setiap seksyen pada satu masa). Setiap peraturan disemak semula semasa kenaikan. Pelajar yang dalam pada itu telah mendaftar kursus lain dan kini melebihi had kredit atau mengalami pertindihan masa dikeluarkan daripada senarai menunggu dengan sebab direkodkan. Pelajar menerima e-mel. Apa-apa yang tertinggal dikendalikan setiap jam oleh `waitlist_promote`.
- Setelah tempoh pendaftaran dan tambah/gugur kesemuanya ditutup, entri senarai menunggu yang berbaki akan luput.
- Kapasiti tidak boleh dikurangkan di bawah bilangan pelajar yang sudah berdaftar.

Tiada cara untuk menyusun semula senarai menunggu. Untuk meletakkan pelajar tertentu di hadapan, gunakan **Daftarkan pelajar** (naikkan kapasiti jika seksyen penuh).

## Skrin pelajar

Dalam portal di bawah **Pendaftaran kursus** (`/portal/registration/`), pelajar memilih semester, mencari mengikut kod kursus atau nama kursus dan mendaftar, menambah ke troli atau menyertai senarai menunggu. Skrin memaparkan keadaan tempoh pendaftaran (dibuka, troli sahaja, masa pembukaan), kredit yang didaftarkan berbanding had kredit dan jadual waktu. Pada telefon, jadual waktu dipaparkan sebagai senarai mengikut hari dalam minggu.

- **Troli**: semasa tempoh troli, pelajar mengumpul kursus dan, setelah pendaftaran dibuka, menekan **Daftar semua**. Menambah ke troli menjalankan peraturan lebih awal dan melaporkan masalah, tetapi hanya semakan tempoh, seksyen dibuka dan kursus sama dua kali yang menghalang penambahan. Peraturan disemak semula semasa pendaftaran.
- Butang gugur dan tarik diri berubah mengikut tempoh urusan. Kursus yang ditarik diri kekal dalam sejarah sebagai **Tarik diri** (dipaparkan sebagai W pada skrin gred, [bab 21](21-grades.md)).
- Daftar, sertai senarai menunggu, tambah ke troli dan daftar semua dihadkan kepada 30 permintaan seminit bagi setiap individu.

## Pendaftaran kursus dan pelarasan oleh kakitangan

**Pendaftaran kursus**: tapis mengikut semester dan status, cari mengikut nombor matrik atau nama. Secara lalai ia memaparkan entri berdaftar bagi semester semasa (atau seterusnya).

**Daftarkan pelajar** (di bahagian atas Pendaftaran kursus, atau butang di bahagian atas halaman seksyen): masukkan nombor matrik, seksyen (hanya apabila dibuka daripada Pendaftaran kursus: seksyen yang diterbitkan bagi semester semasa), peraturan yang hendak diketepikan, sama ada hendak ditambah ke senarai menunggu jika penuh, dan sebabnya.

- Peraturan yang sama seperti bagi pelajar disemak. **Tempoh pendaftaran tidak terpakai bagi pendaftaran oleh kakitangan.**
- "Ketepikan peraturan" hanya berfungsi bagi peraturan dengan **Kelulusan khas dibenarkan** dihidupkan. Seksyen dibuka dan tempat duduk tidak boleh dipilih (naikkan kapasiti sebaliknya).
- Hasilnya (berdaftar, dalam senarai menunggu, ditolak beserta sebab) dipaparkan sebagai mesej di bahagian atas skrin. Hanya pendaftaran yang berjaya direkodkan dalam log aktiviti, bersama sebabnya.

**Gugur dan tarik diri**: daripada menu baris dalam Pendaftaran kursus atau **Gugurkan** / **Tarik diri** dalam tab **Senarai pelajar** seksyen, dengan sebab. Boleh dilakukan tanpa mengira tempoh urusan. Apabila tempat duduk dibebaskan, kenaikan senarai menunggu menyusul.

Tab **Senarai menunggu** (seksyen yang mempunyai saiz senarai menunggu atau entri senarai menunggu): mengikut susunan permintaan, dengan status dan catatan hasil. **Alih keluar** pada sesuatu baris mengeluarkan pelajar dengan sebab. Selepas menaikkan kapasiti, **Naikkan sekarang** di bahagian atas halaman menaikkan pelajar serta-merta.

## Sekatan dan kelulusan khas

**Sekatan** (penafian pendaftaran sistem lama `SRDENY`): **Kenakan sekatan** dengan nombor matrik, jenis sekatan (Tidak mendaftar semester, Kewangan, Akademik, Pentadbiran, Lain-lain), kesan (menyekat pendaftaran / paparan gred / sijil), mula dan tamat, sebab. Sekatan paparan gred dan sijil dimatikan secara lalai. Selain yuran pengajian belum dibayar, ia digunakan untuk kes pentadbiran apabila gred mesti ditahan buat seketika, seperti siasatan salah laku akademik. Dengan sekatan paparan gred, pelajar tidak dapat melihat skrin gred portal atau laporan gred ([bab 21](21-grades.md)). Skrin kakitangan dan kemasukan gred oleh pensyarah tidak terjejas. Dengan sekatan sijil, kakitangan tidak boleh mengeluarkan sijil ([bab 23](23-certificates.md)). Sekatan tidak dipadam; ia **ditarik balik** dengan sebab daripada barisnya. Senarai lalai memaparkan sekatan yang sedang berkuat kuasa. **Import CSV** di atas senarai memuatkan senarai sekali gus ([bab 9](09-csv-import.md#sekatan-pendaftaran)).

**Kelulusan khas** (kebenaran pendaftaran sistem lama `SRALLOW`): **Berikan kelulusan khas** dengan nombor matrik, semester, peraturan, perkara yang dikenakan (kosong: seluruh semester, atau seksyen dalam bentuk `COURSE-SECTION` atau kod kursus), tarikh luput, sebab. Dengan kelulusan khas, pendaftaran diteruskan walaupun peraturan itu gagal (selagi peraturan itu mempunyai Kelulusan khas dibenarkan dihidupkan). Peraturan tempoh pendaftaran juga boleh dibuka melalui kelulusan khas (cth. pelajar yang akan bergraduat yang terlepas tempoh). Seksyen dibuka dan tempat duduk tidak boleh dikecualikan. **Batalkan** kelulusan khas daripada barisnya setelah ia tidak lagi diperlukan.

## Cubaan pendaftaran

Setiap cubaan pendaftaran, pengguguran, tarik diri, senarai menunggu, kenaikan dan troli disimpan bersama masa, hasil, peraturan yang tidak dipenuhi dan mesej, kakitangan atau pelajar yang melakukannya, serta ID permintaan. Tapis mengikut semester, hasil dan tindakan, cari mengikut nombor matrik. Bagi soalan "mengapa saya tidak dapat mendaftar", cari mengikut nombor matrik. Apa yang akan berlaku jika pelajar mendaftar sekarang boleh dipratonton dengan `uv run manage.py registration_simulate {student number} {course code-section number}` (tiada apa-apa disimpan atau direkodkan).

[Kandungan manual pentadbir](README.md)
