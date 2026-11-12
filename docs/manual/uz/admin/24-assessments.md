# 24. Imtihonlar

Menyu: **Imtihonlar > Imtihon sessiyalari**, **Imtihon natijalari**, **Natijalarni tuzatish**, **Imtihon turlari**. Talabalar portaldagi **Imtihonlar** boʻlimida roʻyxatdan oʻtadi va natijalarini koʻradi.

| Ruxsat | Nimaga imkon beradi |
|---|---|
| `Talabalarni roʻyxatga olish, natijalarni kiritish va eʼlon qilish, tashqi natijalarni qayd etish` | Talabalarni roʻyxatga olish, roʻyxatdan chiqarish va kelmagan deb belgilash, natijalarni kiritish, CSV import qilish, natijalarni eʼlon qilish, tuzatish soʻrash, tashqi natijalarni qayd etish va olib tashlash, natijalar reyestrini koʻrish (talaba yozuvlarini koʻrish qamrovi doirasida) |
| `Imtihon turlari, boʻlimlari va sessiyalarini boshqarish` | Turlar, boʻlimlar va sessiyalarni yaratish va tahrirlash, sessiyaning oʻtish balini oʻzgartirish, tuzatish soʻrovlarini tasdiqlash va rad etish |

Rollar boʻyicha standart sozlamalar: Registrator va Oʻquv-uslubiy boshqarmada ikkalasi ham bor. Tur va sessiya ekranlari uchun `Asosiy maʼlumotlarni koʻrish` ham kerak (rollar boʻyicha standart sozlamalarda bor). Natijalar faqat talaba yozuvlarini koʻrish qamrovi doirasida koʻrinadi, shuning uchun `Talaba yozuvlarini koʻrish` (yoki boshqarish) ruxsatini ham bering.

## Eski tizimdan farqlari

- **Har bir tur uchun qatʼiy ustunlar yoʻq.** Eski tizimda (YUSTIC) `CET` da grammatika, yozish, tinglab tushunish va oʻqish degan toʻrtta ustun qattiq belgilangan, kompleks imtihon uchun har bir fanga bitta P/N harfi (`SSCORE_ADD`), kompyuter imtihoni uchun esa yana bir alohida jadval (`COMEXAM`) bor edi. Yangi tizim boʻlimlar va baholash usulini **imtihon turi** da belgilaydi va har bir imtihonni bir xil sessiya, roʻyxatga olish va natija tuzilmasi bilan boshqaradi.
- **Oʻtish qarori.** Eski tizimda toʻrt boʻlim jami oʻtish chegarasiga teng yoki undan yuqori boʻlsa, oʻtgan hisoblanardi, har bir boʻlim uchun minimal ball yoʻq edi. Yangi tizim turning (yoki sessiyaning) oʻtish bali va **har bir boʻlim uchun minimal ball** asosida qaror qiladi va qarorni natijada saqlaydi. Oʻtdi/oʻtmadi turlari boʻyicha qarorni xodimlar qabul qiladi.
- **Roʻyxatga olish muddati va oʻrinlar soni.** Eski tizimda bular yoʻq edi. Sessiyada roʻyxatga olishning ochilish va yopilish vaqti hamda oʻrinlar soni bor.
- **Natijalarni eʼlon qilish.** Eski tizimda talabalar natijalarni kiritilishi bilanoq va faqat oxirgi sessiya uchun koʻrardi. Yangi tizimda talabalar natijalarni sessiyaning **Natijalarni eʼlon qilish** amalidan keyin koʻradi va barcha sessiyalar natijalari saqlanadi. Natijalari bor sessiyani oʻchirib boʻlmaydi.
- **Tashqi natijalar.** Eski tizimda TOEFL yoki TOPIK kabi tashqi testlarni qayd etadigan joy yoʻq edi (bitiruvni tekshirish varaqasidagi HSK katagi boʻsh yozuv edi). Tashqi natijalar tasdiqlovchi fayl bilan qayd etiladi.
- **Bitiruv talablari bilan bogʻlanish.** Eski tizimda bitiruvni tekshirish varaqasini inson oʻqib, qaror qabul qilardi. **Topshirilgan imtihon** talab turi buni oʻquv rejaga kiritadi ([17-bob](17-courses-and-curriculum.md)).

## Imtihon turlari va boʻlimlari

**Imtihon turlari**: kod, nomi (har bir til uchun), toifa (Til, Kompleks, Bitiruv ishi, Tashqi test), baholash usuli, maksimal ball, oʻtish bali, tashqi natijalar, faol, tartib.

| Baholash usuli | Kiritiladigan maʼlumot | Qaror |
|---|---|---|
| Ball | Har bir boʻlim uchun ball (boʻlimlar boʻlmasa, jami) | Jami ≥ oʻtish bali va har bir boʻlim ≥ uning minimal bali. Oʻtish bali boʻlmasa, xodimlar tanlaydi |
| Oʻtdi/oʻtmadi | Oʻtdi yoki oʻtmadi | Xodimlar tanlaydi |

**Boʻlimlar** (tur tahrirlash ekranidagi **Boʻlimlar** yorligʻi): kod (CSV ustuni nomi; harflar, raqamlar, `-`, `_`), nomi, maksimal ball, oʻtish uchun minimal ball (ixtiyoriy), tartib. Boʻlimlar boʻlsa, jami boʻlim ballarining yigʻindisi boʻladi. Boʻlim minimumiga teng ball undan oʻtadi; bir ball kam boʻlsa, jamidan qatʼi nazar talaba oʻtmaydi.

Koreya universiteti profili (`setup_install --profile=korean-university`) yaratadigan turlar:

| Kod | Tur | Qaror | Izoh |
|---|---|---|---|
| `ENG_COMP` | Ingliz tili boʻyicha kompleks imtihon | Ball, 60 dan oʻtiladi | Tinglab tushunish, oʻqish, yozish, grammatika, har biri 25 ball |
| `COMP_EXAM` | Kompyuter savodxonligi boʻyicha kompleks imtihon | Oʻtdi/oʻtmadi | |
| `THESIS` | Bitiruv malakaviy ishi | Oʻtdi/oʻtmadi | |
| `TOPIK` | TOPIK (Koreys tilini bilish darajasi testi) | Oʻtdi/oʻtmadi, tashqi | Daraja va sertifikat raqami qayd etiladi |

Profilni qayta ishga tushirish administratorlar oʻzgartirgan qiymatlarni saqlaydi va ular olib tashlagan boʻlimlarni qaytarmaydi.

## Sessiyalar

**Imtihon sessiyalari**: tur, sana (har bir tur uchun yagona), joy, oʻrinlar soni, roʻyxatga olish ochilishi va yopilishi, oʻtish bali (boʻsh: turning qiymati). Sessiya ekranidagi **Roʻyxatdan oʻtganlar** yorligʻi roʻyxatga olishlarni koʻrsatadi.

- **Talabani roʻyxatga olish** (talaba raqamini kiriting): xodimlar talabalarni roʻyxatga olish muddatidan qatʼi nazar, imtihon sanasigacha roʻyxatga olishi mumkin. Oʻrinlar soni cheklovi amal qiladi. Sanasi oʻtgan sessiyaga hech kimni roʻyxatga olib boʻlmaydi. Natijalar faqat roʻyxatdan oʻtgan talabalar uchun kiritiladi; roʻyxatdan oʻtmagan talabalarning CSV qatorlari xato sifatida koʻrsatiladi va oʻtkazib yuboriladi.
- Talabalar roʻyxatga olish muddati davomida portalda roʻyxatdan oʻtadi va bekor qiladi. Buni faqat oʻqiyotgan va akademik taʼtildagi talabalar qila oladi. Bekor qilgandan keyin qayta roʻyxatdan oʻtish oʻsha roʻyxatga olishni qayta faollashtiradi.
- **Natijani kiritish**: har bir boʻlim uchun ball (yoki jami), kerak boʻlganda oʻtdi yoki oʻtmadi, izoh. Eʼlon qilishdan oldin qayta kiritish uni qayta yozadi (audit hodisasi `assessment.result_recorded`). **Eʼlon qilingandan keyin u bloklanadi** (quyidagi tuzatish soʻrovlariga qarang).
- **Kelmadi**: roʻyxatdan oʻtgan, lekin imtihonga kelmagan. Natija kiritilsa, roʻyxatga olish yana roʻyxatdan oʻtgan holatiga qaytadi.
- **Roʻyxatdan chiqarish**: natijasi bor roʻyxatga olishni bekor qilib boʻlmaydi. Sabab ixtiyoriy.
- **Natijalarni eʼlon qilish**: shundan boshlab talabalar ushbu sessiya natijalarini koʻradi. Eʼlon qilingandan keyin natijalarni bevosita tahrirlab yoki oʻchirib boʻlmaydi; ular **tuzatish soʻrovi** orqali oʻzgaradi (2026-10-23 dagi qaror). `assessment_publish_results` buyrugʻi bilan bir xil.
- Sessiyaning **oʻtish bali** (turnikini bekor qiladi): imtihon qiyin boʻlgani sababli majlis oʻtish chegarasini pasaytirganda qoʻllaniladi. Uni **eʼlon qilishdan oldin** oʻzgartirish mumkin va u saqlanganda shu sessiya uchun allaqachon kiritilgan barcha natijalar saqlangan ballar asosida **qayta baholanadi** (jami yangi chegaraga, boʻlim minimumlari turda belgilanganicha). **Oʻtish balini oʻzgartirish sababi** koʻrsatilganda `assessment.pass_score_changed` audit hodisasi eski va yangi chegaralarni qarori oʻzgargan talabalar raqamlari bilan birga saqlaydi. Saqlangandan keyin ekran nechta natija qayta baholanganini koʻrsatadi. **Eʼlon qilingandan keyin** u faqat koʻrish uchun boʻladi (faqat tuzatish soʻrovlari). Har bir boʻlim uchun minimal ballni sessiyada oʻzgartirib boʻlmaydi (tur sozlamasi).
- **Natijalarni import qilish (CSV)**: format quyida. Roʻyxatdan oʻtmagan talabalar qatorlari xato sifatida oʻtkazib yuboriladi. `assessment_import_results` buyrugʻi bilan bir xil.

CSV formati (sarlavha qatori, UTF-8, 5 MB gacha):

| Ustun | Mazmuni |
|---|---|
| `student_number` | Talaba raqami (majburiy) |
| Boʻlim kodi (`LISTENING`, …) | Boʻlim bali. Katta-kichik harf farqlanmaydi |
| `total` | Boʻlimlarsiz turlar uchun jami |
| `passed` | `Y`/`N`. Oʻtdi/oʻtmadi turlari yoki oʻtish bali boʻlmagan turlar uchun majburiy |
| `absent` | `Y` talabani kelmagan deb belgilaydi |
| `note` | Izoh |

Xato qatorlar oʻtkazib yuboriladi va natija xabarlarida (ekran, birinchi 10 tasi) yoki chiqishda (buyruq) qator raqami bilan koʻrsatiladi. Xato matnlari buyruq chiqishi kabi ingliz tilida.

## Natijalarni tuzatish

Eʼlon qilingan sessiya natijalarini oʻzgartirish tartibi. U baholarni oʻzgartirish kabi ishlaydi.

1. Sessiyaning **Roʻyxatdan oʻtganlar** yorligʻida **Tuzatishni soʻrash**: yangi ballar (yoki oʻtdi yoki oʻtmadi) va sabab. Har bir natija uchun bitta koʻrib chiqilayotgan soʻrov. Audit hodisasi `assessment.correction_requested`.
2. **Imtihonlar > Natijalarni tuzatish** boʻlimida `Imtihon turlari, boʻlimlari va sessiyalarini boshqarish` ruxsatiga ega xodim **Tasdiqlash** (izoh ixtiyoriy) yoki **Rad etish** (izoh majburiy) tugmasini bosadi. **Hech kim oʻz soʻrovi boʻyicha qaror qabul qila olmaydi.**
3. Tasdiqlanganda natija darhol yangi qiymatlarga oʻzgaradi (qaror yangi ballar asosida qayta qabul qilinadi) va talaba uni koʻradi. Audit hodisalari `assessment.correction_approved`, `assessment.result_corrected`. Soʻrov beruvchi qaror qabul qilinguncha soʻrovni bekor qilishi mumkin.

Roʻyxat standart holatda koʻrib chiqilayotgan soʻrovlarni (barcha soʻrovlar uchun holat filtri **Hammasi**) joriy qiymatlar va taklif etilgan qiymatlar bilan yonma-yon koʻrsatadi. Menyu koʻrib chiqilayotgan soʻrovlar sonini koʻrsatadi.

## Natijalar reyestri

**Imtihon natijalari**: barcha natijalar (sessiyalar va tashqi). Tur, manba va oʻtganlik boʻyicha filtrlang; talaba raqami yoki ism boʻyicha qidiring. Koʻrish qamrovi talaba yozuvlariniki bilan bir xil.

- **Tashqi natijani qayd etish** (roʻyxat ustida): talaba raqami, tur (faqat tashqi natijalarga ruxsat beruvchi turlar), topshirilgan sana (kelajakdagi sana emas), jami, daraja, oʻtdi yoki oʻtmadi, sertifikat raqami, tasdiqlovchi fayl (PDF, JPG, PNG, 5 MB), izoh. Audit hodisasi `assessment.external_recorded`.
- **Tasdiqlovchi hujjat**: faylni ochadi. Talabalar oʻz fayllarini ocha oladi.
- **Olib tashlash** (qator): sabab majburiy, audit hodisasi `assessment.result_removed`. Notoʻgʻri kiritilgan tashqi natijani yoki eʼlon qilinmagan natijani oʻchirib, qayta qayd etish uchun. Tasdiqlovchi fayl ham oʻchiriladi. Eʼlon qilingan sessiya natijalarini olib tashlab boʻlmaydi (tuzatish soʻrovi).

## Bitiruv talablari

**Oʻquv reja > Bitiruv talablari** boʻlimida **Topshirilgan imtihon** talab turini tanlang va **Imtihon turi** ni tanlang. Talaba bu talabni shu turdagi kamida bitta oʻtgan natija (sessiya yoki tashqi) bilan bajaradi. Portaldagi **Imtihonlar** sahifasining yuqori qismida talabaning oʻquv rejasi talab qiladigan turlar va ulardan oʻtilganligi koʻrsatiladi. Bitiruv talablarini tekshirish ([26-bob](26-graduation.md)) bu talabni oʻqiydi. Talabda ishlatilgan turni oʻchirib boʻlmaydi (uning oʻrniga faolsizlantiring).

## Talaba portali

**Imtihonlar**: oʻquv reja talablari va ulardan oʻtilganligi, roʻyxatga olish ochiq sessiyalar (roʻyxatdan oʻtish, bekor qilish), mening roʻyxatdan oʻtishlarim, mening natijalarim (eʼlon qilingan sessiyalar va tashqi natijalar, boʻlim ballari, tasdiqlovchi hujjat).

## Ushbu oʻrnatmadagi ekranlar

Ekranlar va funksiyalar asl tizimnikidek (Filament, Livewire); ulardan foydalanish biroz farq qiladi.

- **Imtihon sessiyalari** roʻyxatining qator menyusi: **Natijalarni eʼlon qilish** (tasdiqlash sahifasi), **Natijalarni import qilish (CSV)** (fayl sahifasi). Sessiya ekrani yuqorisidagi tugmalar: **Talabani roʻyxatga olish** (imtihon sanasigacha), **Natijalarni import qilish (CSV)**, **Natijalarni eʼlon qilish**. Filtrlar: tur, natijalar eʼlon qilingan.
- Sessiya ekranidagi **Roʻyxatdan oʻtganlar** yorligʻi holatni bosish orqali filtrlanadi (Hammasi, Roʻyxatdan oʻtgan, Bekor qilingan, Kelmadi). Qatordagi **Natijani kiritish**, **Tuzatishni soʻrash**, **Kelmadi** va **Roʻyxatdan chiqarish** havolalari kiritish sahifasini ochadi. Natija sahifasida turning har bir boʻlimi uchun ball maydoni bor va ballar asosida qaror qilinadigan turlar uchun qoida tushuntiriladi.
- **Imtihon natijalari** roʻyxati ustida **Tashqi natijani qayd etish**, qator menyusida **Olib tashlash**. Tasdiqlovchi hujjat ustunidagi havola faylni yangi oynada ochadi.
- **Natijalarni tuzatish** qator menyusi: **Tasdiqlash**, **Rad etish**, **Soʻrovni bekor qilish** (oʻz soʻrovlari).
- Tasdiqlovchi hujjat manzili: `/assessment-results/{result ID}/evidence/` (ruxsat tekshiruvidan keyin yuklab olinadi). Portal manzili: `/portal/assessments/`.
- Buyruqlar: `uv run manage.py assessment_import_results {kind code} {date} {CSV} --actor=... [--dry-run]`, `uv run manage.py assessment_publish_results {kind code} {date} --actor=...` ([operatsion buyruqlar](../operations/commands.md)).

## Koʻp beriladigan savollar

- **Talabani roʻyxatga olish muddatidan tashqarida roʻyxatga olishim kerak.** Xodimlar ularni sessiya ekranidagi **Talabani roʻyxatga olish** orqali roʻyxatga oladi.
- **Oʻtish balini faqat shu sessiya uchun oʻzgartirmoqchiman.** Eʼlon qilishdan oldin sessiyaning oʻtish balini sabab bilan kiriting va saqlang. Allaqachon kiritilgan natijalar darhol yangi chegara boʻyicha baholanadi.
- **Ballni notoʻgʻri kiritdim.** Eʼlon qilishdan oldin uni qayta yozish uchun yana **Natijani kiritish**. Eʼlon qilingandan keyin **tuzatish soʻrovi** yuboring va uni boshqa xodimga tasdiqlating.
- **Kelmaganlar statistikasi.** **Roʻyxatdan oʻtganlar** yorligʻini **Kelmadi** holati boʻyicha filtrlang.

[Administrator qoʻllanmasi mundarijasi](README.md)
