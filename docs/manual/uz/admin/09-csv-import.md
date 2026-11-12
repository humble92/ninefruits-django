# 9. CSV import

Tashkiliy birliklar, taʼlim dasturlari, binolar, auditoriyalar va kodlar roʻyxati ekranlarining yuqorisidagi **CSV import qilish** tugmasidan foydalaning (`Asosiy maʼlumotlarni CSV dan import qilish` ruxsati). Talaba yozuvlari, oʻqituvchilar, fanlar va yozilish cheklovlari ham xuddi shu tarzda import qilinadi (quyida). Juda katta fayllarni IT operatori `reference_import` buyrugʻi bilan xuddi shu tarzda import qilishi mumkin.

## Umumiy qoidalar

- Birinchi qatorda ustun nomlari boʻladi (quyidagi jadvallarga qarang). Kodlash UTF-8; Excel da "CSV UTF-8" formatida saqlang.
- Kodi allaqachon mavjud boʻlgan qator shu yozuvni **yangilaydi**. Bir xil faylni qayta import qilish takroriy yozuvlar yaratmaydi.
- Tillarga bogʻliq ustunlar `ustun_til` koʻrinishida yoziladi: `name_en`, `name_ko`, `name_zh-hans`. Yangi qatorlar uchun inglizcha nom (`name_en`) majburiy. Boʻsh katakchalar mavjud tarjimalarni oʻchirmaydi.
- Sanalar `2026-03-01` koʻrinishida yoziladi; ha/yoʻq qiymatlari `1`/`0` yoki `true`/`false`.
- Avval sarlavha tekshiriladi (majburiy ustun yetishmasa, hech narsa import qilinmaydi). 500 qatorgacha boʻlgan fayllar darhol import qilinadi; kattaroq fayllar fon rejimida (Celery) qayta ishlanadi. Natija **Asosiy maʼlumotlar > CSV importlar** dagi import sahifasida koʻrsatiladi (import qilingan qatorlar, xatoli qatorlar va ularning sabablari). Agar xatoli qatorlar boʻlsa, **Xatoli qatorlarni yuklab olish** orqali har bir qator uchun sabab koʻrsatilgan CSV olinadi. Uni tuzating va faqat shu faylni qayta import qiling.
- Ustun nomlari quyidagi jadvallarga mos boʻlishi kerak; nomaʼlum ustunlar eʼtiborga olinmaydi. Asl tizimdagi `name_zh_CN` ustun nomi `name_zh-hans` sifatida qabul qilinadi.

## Ustun formatlari

| Tur | Majburiy ustunlar | Ixtiyoriy ustunlar |
|---|---|---|
| Tashkiliy birliklar | `code`, `type` (tashkiliy birlik turi kodi), `name_en`, `effective_start_date` | `parent` (yuqori birlik kodi), `name_ko` va h.k., `short_name_*`, `effective_end_date`, `sort_order` |
| Taʼlim dasturlari | `code`, `org_unit` (tashkiliy birlik kodi), `degree_level`, `name_en`, `effective_start_date` | `degree_title_*`, `standard_duration_years`, `effective_end_date`, `allows_second_major`, `allows_minor` |
| Binolar | `code`, `name_en` | `name_*`, `address`, `is_active` |
| Auditoriyalar | `building` (bino kodi), `code` (auditoriya raqami) | `name_*`, `room_type` (auditoriya turi kodi), `org_unit`, `capacity`, `is_schedulable`, `is_active` |
| Kod qiymatlari | `type` (roʻyxat kodi), `code`, `name_en` | `name_*`, `sort_order`, `is_active` |

`degree_level` qiymatlari: `associate`, `bachelor`, `master`, `doctorate`, `certificate`, `non_degree`

Tashkiliy birliklarda yuqori birliklar oldin kelishi kerak (universitet → fakultet → kafedra tartibida saralang).

## Misol: tashkiliy birliklar

```csv
code,type,parent,name_en,name_ko,effective_start_date
UNI,university,,Sample University,샘플대학교,1990-03-01
ENG,college,UNI,College of Engineering,공과대학,1990-03-01
CSE,department,ENG,Computer Science,컴퓨터공학과,1995-03-01
```

## Talabalar va oʻqituvchilar

Talaba yozuvlari `student_number` boʻyicha, oʻqituvchilar `employee_number` boʻyicha moslashtiriladi va yangilanadi. Ikkala tur shaxs ustunlarini birgalikda ishlatadi.

| Tur | Yangi qatorlar uchun majburiy ustunlar | Ixtiyoriy ustunlar |
|---|---|---|
| Talaba yozuvlari | `student_number`, `program` (taʼlim dasturi kodi), `admission_date`, `family_name` | `catalog_year` (boʻsh boʻlsa, qabul yili), `year_level`, `status`, `graduation_date`, `institutional_email` |
| Oʻqituvchilar | `employee_number`, `org_unit` (tashkiliy birlik kodi), `employment_type`, `family_name` | `academic_title_*`, `hire_date`, `end_date` |
| Shaxs ustunlari (umumiy) | — | `given_name`, `name_ko` kabi tillar boʻyicha ismlar, `birth_date`, `gender`, `email`, `phone`, `national_id` |

- `status` qiymatlari: `enrolled`, `on_leave`, `withdrawn`, `dismissed`, `graduated` (graduated uchun `graduation_date` majburiy). Import orqali oʻzgartirilgan maqom **maʼlumotni tuzatish** hisoblanadi va maqom oʻzgarishi tarixini yaratmaydi. Haqiqiy oʻzgarishlar ekranda qayd etiladi ([13-bob](13-status-changes-and-advisors.md)).
- `employment_type` qiymatlari: `full_time`, `part_time`, `adjunct`, `visiting`, `emeritus`. `gender` qiymatlari: `female`, `male`, `other`, `undisclosed`.
- Agar yangi talaba yozuvining `national_id` qiymati mavjud shaxsnikiga mos kelsa, yozuv shu shaxsga biriktiriladi (oʻqishga qayta tiklash). Aks holda yangi shaxs yaratiladi. Yangilashda boʻsh katakchalar mavjud qiymatlarni oʻchirmaydi.
- Import qilingan talabalar va oʻqituvchilarning hisobi boʻlmaydi. Ularga [hisobga taklif qilish](14-merge-and-invitations.md#hisobga-taklif-qilish) orqali taklifnoma yuboring.

```csv
student_number,program,admission_date,year_level,status,family_name,given_name,name_ko,birth_date
202600001,B-CSE,2026-03-02,1,enrolled,Kim,Minsu,김민수,2007-05-01
```

Fan versiyalarini import qilish [17-bobda](17-courses-and-curriculum.md), yozilish cheklovlarini import qilish [20-bobda](20-registration.md) tasvirlangan.

## Yozilish cheklovlari

**Fanlarga yozilish > Cheklovlar** roʻyxati yuqorisidagi **CSV import qilish** (`Cheklov qoʻyish va olib tashlash, qoidalardan istisno berish` ruxsati) yoki `uv run manage.py reference_import registration_holds`. Eski tizimdagi `SRDENY` maʼlumotlarini yoki moliya boʻlimining toʻlov qilmagan talabalar roʻyxatini yuklash uchun ishlatiladi.

| Majburiy ustunlar | Ixtiyoriy ustunlar |
|---|---|
| `student_number`, `hold_type` (`unregistered`, `financial`, `academic`, `administrative`, `other`), `reason` | `starts_at` (standart: import vaqti), `ends_at`, `blocks_registration` (standart 1), `blocks_grades`, `blocks_certificates` |

- Har bir qator yangi cheklov yaratadi (manba `import`). Bir xil faylni ikki marta import qilish cheklovlarni ikki marta yaratadi, shuning uchun qayta import qilishdan oldin roʻyxatni tekshiring.
- Vaqtlar `2027-03-15` yoki `2027-03-15 09:00` koʻrinishida yoziladi (vaqt mintaqasi koʻrsatilmasa, server vaqti, UTC). `ends_at` `starts_at` dan keyin boʻlishi kerak.
- Nomaʼlum talaba raqamli qatorlar muvaffaqiyatsiz boʻladi. Cheklovlar ekranda sabab koʻrsatilgan holda olib tashlanadi ([20-bob](20-registration.md)).

```csv
student_number,hold_type,reason,ends_at
202312345,financial,Tuition unpaid 2027-1,
202254321,academic,Probation meeting needed,2027-03-15
```
