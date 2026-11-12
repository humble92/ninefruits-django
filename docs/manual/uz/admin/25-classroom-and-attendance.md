# 25. Oʻqituvchi auditoriyasi va davomat

Menyu: oʻqituvchilar portaldagi **Mening darslarim > Roʻyxat va davomat** (`/portal/sections/{section ID}/attendance/`) dan, talabalar portaldagi **Davomat** (`/portal/attendance/`) dan foydalanadi. Xodimlar boshqaruv panelidagi **Oʻquv reja va fan guruhlari > Fan guruhlari > Oʻzgartirish** ekranining **Darslar** yorligʻidan foydalanadi.

| Kim | Nima qila oladi |
|---|---|
| Tayinlangan oʻqituvchilar | Talabalar roʻyxati (suratlar bilan) va CSV, davomat jurnali PDF, darslarni yaratish, qoʻshish va bekor qilish, davomatni kiritish |
| `Fan guruhlarini rejalashtirish (oʻqituvchilar, vaqtlar, auditoriyalar)` ruxsatiga ega xodimlar (qamrov doirasida) | Oʻqituvchilar bilan bir xil + boshqaruv panelidagi darslar |
| `Fan guruhlarini koʻrish` ruxsatiga ega xodimlar (qamrov doirasida) | Talabalar roʻyxati, davomat jurnali, davomatni koʻrish |
| Talabalar | Oʻz davomati |

Eʼlonlar, topshiriqlar va materiallar kabi auditoriya funksiyalari LMS ga qoldirilgan (koʻchirish rejasi, 12-boʻlim).

## Eski tizimdan farqlari

- **Eski tizim (YUSTIC) davomatni qayd etmasdi.** Uning "davomat jurnali" talabalar roʻyxati yonida boʻsh kataklarni (nusxaga qarab 27 tadan 34 tagacha) chop etadigan PDF boʻlib, unda sanalar ham, jamilar ham yoʻq edi. Yangi tizim dars vaqtlaridan **darslar** yaratadi, har bir dars uchun qatnashdi, kechikdi, qatnashmadi yoki sababli holatini qayd etadi va yozuvlar hamda jamilarni davomat jurnali PDF ida chop etadi.
- **Talabalar roʻyxati.** Eski tizimning oʻqituvchi ekrani faqat talaba raqamlari va ismlarini koʻrsatardi (va qalqib chiquvchi oynada fuqarolik roʻyxatga olish raqami va manzilni oshkor qilardi), Excel yuklab olish imkoni ham yoʻq edi. Yangi tizim faqat talaba raqami, ism, surat, taʼlim dasturi, kurs va aloqa e-pochtasini koʻrsatadi va CSV sifatida yuklab beradi. Yuklab olishlar audit jurnalida qayd etiladi.
- **Oʻqituvchilarning oʻz talabalariga kirishi.** Oʻqituvchilar oʻz fan guruhlaridagi talabalarning talaba yozuvlari va shaxslarini koʻra olishiga qator darajasidagi xavfsizlik siyosati (`student_records_instructor_select`, `util.taught_student_record_ids()` funksiyasi) imkon beradi va ilovaning koʻrinish qoidalari unga mos keladi (avval asl tizim ularga faqat oʻz maslahat oluvchilarini koʻrsatardi, shu sababli hatto baho kiritish ekranida ham ismlar boʻsh qolardi).

## Darslar

- **Yaratish**: haftalik dars vaqtlarining (kun, vaqt, para) har bir takrori uchun bitta dars. Oʻqituvchilar **Dars vaqtlaridan yaratish** tugmasidan, xodimlar esa **Darslar** yorligʻi ustidagi **Darslarni yaratish** tugmasidan (tasdiqlash sahifasi bilan) yoki `uv run manage.py attendance_generate_sessions {term}` buyrugʻidan (butun semestr) foydalanadi. Mavjud darslar va davomatga tegilmaydi, shuning uchun dars vaqtlari oʻzgargandan keyin uni qayta ishga tushirish mumkin. Bekor qilingan fan guruhlari oʻtkazib yuboriladi.
- **Dars qoʻshish**: dars vaqtlaridan tashqari dars, masalan qoʻshimcha (oʻrnini toʻldiruvchi) dars (sana, boshlanishi, tugashi). Faqat mashgʻulotlar davri ichidagi sanalar va bir sana hamda boshlanish vaqtiga faqat bitta dars.
- **Bekor qilish**: darsni sabab koʻrsatib bekor qiling. Dars saqlanib qoladi, lekin jamilarga kiritilmaydi. **Tiklash** uni qaytaradi.
- Bayramlar taqvimi yoʻq. Bayram kunlaridagi darslarni bekor qiling (semestr taqvimi qoʻshilgach, yaratuvchi ularni chiqarib tashlashi mumkin boʻladi).

## Davomatni kiritish

Darsning **Davomat** boʻlimida har bir talaba uchun qatnashdi, kechikdi, qatnashmadi yoki sababli holatini tanlang, izoh qoʻshing (200 belgi) va **Davomatni saqlash** ni bosing. Eng tez usul — **Hammasi qatnashdi** ni bosib (saqlamasdan hammani qatnashdi deb belgilaydi), soʻngra istisnolarni oʻzgartirish.

- Davomatni dars kunidan boshlab kiritish mumkin (kelajakdagi yoki bekor qilingan darslar uchun emas).
- Qayta saqlanganda faqat oʻzgargan talabalar qayd etiladi va audit hodisasi (`attendance.recorded`) har bir talaba boʻyicha eski va yangi qiymatni saqlaydi.
- Holatni tozalash talabani "qayd etilmagan" holatiga qaytaradi.
- Faqat yozilgan va fanni tugatgan talabalarni qayd etish mumkin (fandan chiqqan va voz kechgan talabalar roʻyxatda yoʻq).

## Jamilar

| Band | Taʼrif |
|---|---|
| Oʻtkazilgan darslar | Bekor qilinmagan va bugun yoki undan oldin boʻlgan darslar |
| Davomat foizi | (qatnashdi + kechikdi + sababli) ÷ oʻtkazilgan darslar × 100, bitta kasr xonasi (yarmi yuqoriga yaxlitlanadi) |
| Qayd etilmagan | Yozuvsiz oʻtkazilgan darslar |

Maʼlum miqdordagi kechikishlarni bitta qatnashmaslikka aylantiradigan yoki darslarning uchdan biridan koʻpiga qatnashmaganlikda F qoʻyadigan qoida yoʻq. Bu universitetlar orasida farq qiladi, shuning uchun oʻqituvchilar davomatni bahoda oʻzlari aks ettiradi. Hisoblash qoidalari bitta xizmatda (`AttendanceSummary`) joylashgan, shuning uchun talabalar roʻyxati, davomat jurnali va talaba sahifasi bir xil raqamlarni koʻrsatadi.

## Davomat jurnali PDF va talabalar roʻyxati CSV

Ikkala yuklab olish ham audit jurnalida qayd etiladi (`attendance.sheet_exported`, `attendance.roster_exported`). `=`, `+`, `-` yoki `@` (yoki tabulyatsiya yoki qator uzilishi) bilan boshlanadigan CSV qiymatlari formula sifatida bajarilmasligi uchun boshiga bitta tirnoq qoʻyilib eksport qilinadi.

- **Davomat jurnali (PDF)** (`/sections/{section ID}/attendance-sheet`): albom formatidagi A4. Talabalar pastga, darslar yonga (bekor qilinganlari kiritilmaydi), O/△/X/E belgilari va har bir talaba boʻyicha jamilar. Hali boʻlmagan darslar boʻsh qoladi, shuning uchun u qoʻlda qayd etish uchun ham xizmat qiladi. PDF serveri (Gotenberg) javob bermasa, "PDF yaratib boʻlmadi" koʻrsatiladi.
- **Talabalar roʻyxati (CSV)** (`/sections/{section ID}/roster.csv`): talaba raqami, ism, taʼlim dasturi, kurs, aloqa e-pochtasi, fanga yozilish holati. BOM bilan UTF-8, shuning uchun Excel da toʻgʻridan-toʻgʻri ochiladi.

## Talaba portali

**Davomat**: har bir semestr (standart holatda boshlangan oxirgi semestr) va fan boʻyicha qatnashgan, kechikkan, qatnashmagan va sababli darslar soni hamda davomat foizi; kengaytirilganda har bir oʻtkazilgan dars boʻyicha yozuv (faqat oʻqituvchi kiritgan maʼlumotlar, aks holda "Qayd etilmagan").

## Ish tartibi

1. Semestr boshlanishidan oldin fan guruhlarining dars vaqtlarini yakunlang ([18-bob](18-sections-and-timetables.md)).
2. Darslarni `uv run manage.py attendance_generate_sessions {term} --actor=...` bilan yarating (oʻqituvchilar ularni ekranda ham yaratishi mumkin). Faqat bitta fan guruhi: `--section=CSE2010-01`; faqat fan guruhlari soni: `--dry-run` ([operatsion buyruqlar](../operations/commands.md)).
3. Dars vaqtlari oʻzgarganda uni qayta ishga tushiring. Olib tashlangan vaqtlarning darslari avtomatik oʻchirilmaydi; ularni bekor qiling.

## Ushbu oʻrnatmadagi ekranlar

Ekranlar va funksiyalar asl tizimnikidek (Filament, Livewire); baʼzi boshqaruv elementlari biroz boshqacha ishlaydi.

- Boshqaruv panelidagi fan guruhini oʻzgartirish ekranining **Darslar** yorligʻi: sana, vaqt, auditoriya, holat, kiritilgan yozuvlar, sabab. Qatordagi **Bekor qilish** sabab sahifasini, **Tiklash** tasdiqlash sahifasini ochadi. **Darslarni yaratish** ekran yuqorisidagi amal tugmasi. Faqat `Fan guruhlarini koʻrish` ruxsatiga ega xodimlar yorliqni tugmalarsiz koʻradi.
- Oʻqituvchi portalida **Bekor qilish** dars qatorida sabab maydonini ochadi; sababni kiriting va yana **Bekor qilish** ni bosing (asl tizimdagi brauzer soʻrovi oʻrniga).
- **Davomat** kiritish sahifasi `?meeting={meeting ID}` bilan tugaydi, shuning uchun uni xatchoʻplarga qoʻshish mumkin. **Orqaga** talabalar roʻyxati va darslar roʻyxatiga qaytaradi.
- Qator darajasidagi xavfsizlik ostida talabalar roʻyxati faqat fanga yozilishlar va talaba yozuvlarini koʻra oladigan shaxslar uchun toʻldiriladi. Standart rollar (Oʻquv-uslubiy boshqarma, Kafedra yordamchisi) `Fanlarga yozilishlar va talabalar roʻyxatlarini koʻrish` va `Talaba yozuvlarini koʻrish` ruxsatlariga ham ega. Faqat `Fan guruhlarini rejalashtirish` berilgan rol boʻsh roʻyxat va jurnalni koʻradi (asl tizimdagidek).

[Administrator qoʻllanmasi mundarijasi](README.md)
