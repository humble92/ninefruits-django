# 27. Hisobotlar va reporting koʻrinishlari

Menyu: **Hisobotlar > Hisobotlar** (`Standart hisobotlarni koʻrish va yuklab olish` ruxsati). Rollar boʻyicha standart sozlamalar: Registrator, Oʻquv-uslubiy boshqarma, Kafedra yordamchisi (qamrov doirasida).

## Standart hisobotlar

Hisobot va uning filtrlarini tanlang: ekranda 500 tagacha qator koʻrsatiladi, **CSV yuklab olish** esa barchasini yuklab beradi (BOM bilan UTF-8, Excel da toʻgʻridan-toʻgʻri ochiladi). Yuklab olishlar `reports.exported` audit hodisasida va `data.exported` xavfsizlik jurnali hodisasida (hisobot, filtrlar, qatorlar soni) qayd etiladi. `=`, `+`, `-`, `@` (yoki tabulyatsiya yoki qator uzilishi) bilan boshlanadigan qiymatlar Excel ularni formula sifatida bajarmasligi uchun boshiga bitta tirnoq (`'`) qoʻyilib eksport qilinadi.

| Hisobot | Filtrlar | Mazmuni |
|---|---|---|
| Talabalar roʻyxati | Tashkiliy birlik (quyi boʻlinmalari bilan birga), holat, kurs | Talaba raqami, ism, taʼlim dasturi, tashkiliy birlik, kurs, holat, qabul sanasi, bitirish sanasi, diplom raqami |
| Boʻlinma, dastur, kurs va holat boʻyicha talabalar soni | Tashkiliy birlik, holat | Talabalar soni |
| Semestr baholari xulosasi (ogohlantirishlar, imtiyozlar) | Semestr, akademik holat | Semestr va umumiy kreditlar hamda GPA, akademik ogohlantirishlar soni, imtiyozlar reytingi ([21-bob](21-grades.md)) |
| Bitiruvga nomzodlar (oxirgi tekshiruv) | Bajarilgan yoki yoʻq | Har bir talaba va dastur boʻyicha oxirgi bitiruv talablari tekshiruvi ([26-bob](26-graduation.md)) |
| Maqom oʻzgarishlari | Semestr, davr | Oʻzgarish turi, oldingi va keyingi holatlar, kuchga kirish sanasi, soʻrov holati |
| Fan guruhlari boʻyicha yozilganlar | Semestr, tashkiliy birlik | Fan guruhi, oʻqituvchilar, oʻrinlar soni, yozilganlar, kutayotganlar |
| Semestrda fanlarga yozilmagan talabalar | Semestr, tashkiliy birlik | Shu semestrda fanlarga yozilmagan oʻqiyotgan talabalar |

Koʻrinadigan maʼlumotlar koʻruvchining ruxsat qamroviga (talaba yozuvlarini koʻrish qamrovi va shu kabilar) bogʻliq. Eski tizimning (YUSTIC) toʻlov va kontrakt hisobotlari (toʻlanmagan kontrakt va shu kabilar) qamrovdan tashqarida va mavjud emas.

## reporting koʻrinishlari

Hisobotlar maʼlumotlar bazasidagi `reporting` sxemasining koʻrinishlarini (view) oʻqiydi. BI vositalari va SQL foydalanuvchilari xuddi shu koʻrinishlarga faqat oʻqish uchun moʻljallangan `app_reporting` roli bilan soʻrov yuboradi.

| Koʻrinish | Mazmuni |
|---|---|
| `reporting.students` | Talaba yozuvi + shaxs ismi + dastur va tashkiliy birlik nomlari |
| `reporting.headcount` | Tashkiliy birlik, dastur, kurs va holat boʻyicha talabalar soni |
| `reporting.term_records` | Har bir semestr boʻyicha baholar xulosasi |
| `reporting.course_grades` | Har bir fan boʻyicha baholar (yakunlangan yoki yoʻq, baho, oʻzlashtirilgan, qayta oʻqish) |
| `reporting.section_enrollments` | Har bir fan guruhi boʻyicha yozilganlar va kutayotganlar, oʻqituvchilar |
| `reporting.section_meetings` | Dars vaqtlari va auditoriyalar |
| `reporting.status_changes` | Maqom oʻzgarishlari |
| `reporting.degree_audits` | Har bir talaba va dasturdagi oʻrin boʻyicha oxirgi bitiruv talablari tekshiruvi |

- Tarjima qilingan ustunlar (`program_name` va shu kabilar) sessiya tiliga bogʻliq: `SET app.locale = 'ko';`. Xom jsonb ustunlari (`program_name_i18n` va shu kabilar) ham mavjud.
- Koʻrinishlar `security_invoker` boʻlgani sababli koʻruvchining qator darajasidagi xavfsizlik (RLS) siyosati oʻzgarishsiz qoʻllaniladi. Talaba hisobi bilan oʻqilganda ular faqat shu talabaning qatorlarini qaytaradi.
- Koʻrinishlar taʼriflari `db/sql/views/reporting.sql` da joylashgan (asl `database/sql/views/reporting.sql` oʻzgarishsiz); oʻzgartirilgandan keyin ular `core` migratsiyasi orqali qayta qoʻllaniladi. Ilova ularni boshqarilmaydigan (unmanaged) modellar orqali oʻqiydi (`ninefruits.reporting.models`, masalan `ReportStudent`).

Eski `AV_*` koʻrinishlari (taxminan 90 ta) ishlatilmagan va koʻchirilmagan.

## Ushbu oʻrnatmadagi ekranlar

- **Hisobotlar > Hisobotlar** (`/admin/reports/`): hisobotni tanlang va uning filtrlarini chiqarish uchun **Koʻrsatish** ni bosing (asl tizim hisobot tanlanishi bilanoq ularni oʻzgartirardi). Filtrlarni toʻldiring va yana **Koʻrsatish** ni bosing. Semestr filtri bor hisobotda semestr tanlanmaguncha qatorlar boʻlmaydi.
- CSV manzili `/reports/{report}.csv?filter=value` (masalan, `/reports/students.csv?status=enrolled`). Faqat roʻyxatdagi hisobot va filtr nomlari qabul qilinadi, ustunlar va tartib esa hisobot taʼrifida belgilangan.
- CSV dagi vaqtlar (audit qilingan, qaror qabul qilingan) asl tizimdagidek UTC dagi PostgreSQL matni sifatida yoziladi (`2026-10-24 07:26:59+00`); sanalar `YYYY-MM-DD`, rost/yolgʻon `Y`/`N`.
- Fan guruhlari boʻyicha yozilganlar hisobotining birlik filtri birlik kodi boʻyicha filtrlaydi (koʻrinishda birlik ID si yoʻq). Asl tizimda bu filtrni tanlash xatoga olib kelardi.
- Fan guruhlari va dars vaqtlarida qator darajasidagi xavfsizlik yoʻq, shuning uchun har bir fan guruhi qatori koʻrsatiladi. Yozilganlar va kutayotganlar soni faqat oʻquvchi koʻra oladigan fanga yozilishlar va kutish roʻyxati yozuvlarini hisoblaydi.

[Administrator qoʻllanmasi mundarijasi](README.md)
