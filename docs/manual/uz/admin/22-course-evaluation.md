# 22. Fan soʻrovnomasi

Menyu: **Fan soʻrovnomasi > Semestr soʻrovnomalari**, **Soʻrovnoma shakllari**, **Fan guruhlari boʻyicha javoblar**, **Sozlamalar > Fan soʻrovnomasi**. Talabalar portaldagi **Fan soʻrovnomasi** dan, oʻqituvchilar esa portaldagi **Mening darslarim > Fan soʻrovnomasi natijalari** dan foydalanadi.

| Ruxsat | Nimaga imkon beradi |
|---|---|
| `Fan soʻrovnomasi javob ulushi va natijalarini koʻrish` | Fan guruhlari boʻyicha javoblar soni va javob berish ulushi, eʼlon qilingan natijalar. Tashkiliy birlik qamrovi bilan tayinlanganda faqat shu boʻlinma ochgan fan guruhlari |
| `Soʻrovnoma shakllari, semestr soʻrovnomalari va eʼlon qilishni boshqarish` | Shakllar va savollar, semestr soʻrovnomasi sozlamalari, natijalarni eʼlon qilish, fan soʻrovnomasi sozlamalari |

Rollar boʻyicha standart sozlamalar: Oʻquv-uslubiy boshqarmada ikkalasi ham, Kafedra yordamchisida koʻrish ruxsati bor (kafedra qamrovi).

## Eski tizimdan farqlari

- **Anonimlik.** Eski tizim (YUSTIC) har bir javob bilan birga talaba raqamini saqlardi va oʻqituvchi hisoblari xom jadvalni oʻqiy olardi. Yangi tizim **kim baholagani (yakunlash yozuvlari)** va **nima javob berilgani (javoblar)** ni alohida saqlaydi. Javobda na talaba, na tartib raqami, na vaqt boʻladi. Javoblar maʼlumot oʻzgarishi yozuviga (audit) ham yozilmaydi, chunki audit yozuvi amalni bajargan shaxsni saqlab qoladi.
- **Natijalarni koʻrsatish chegarasi.** Eski tizimda oʻqituvchi ekranida minimal javoblar chegarasi yoʻq edi va oʻqituvchilar boshqa fan guruhlarining natijalarini koʻra olardi. Yangi tizim natijalar va fikrlarni semestr natijalari **eʼlon qilingan**dan keyin **faqat minimal javoblar soni va minimal javob berish ulushiga yetgan fan guruhlari uchun** koʻrsatadi. Oʻqituvchilar faqat oʻz fan guruhlarini koʻradi.
- **Baholarni koʻrishni toʻsish.** Eski tizim faqat menyu havolasini toʻsardi va soʻrovnoma muddati tugaganda blok olib tashlanmasdi. Yangi tizim serverda toʻsadi va muddat yopilganda blokni olib tashlaydi.
- **Savollarni boshqarish.** Eski tizim har semestr savollarni SQL orqali qoʻshardi. Yangi tizim shakllar va savollarni ekranda boshqaradi.
- Hammasi 1 yoki hammasi 5 boʻlgan javoblarni rad etish qoidasi sozlamaga aylandi (standart holatda oʻchiq).

## Semestrni tayyorlash

1. **Shakl**: **Soʻrovnoma shakllari** boʻlimida shaklni tanlang. Koreya universiteti profili `STANDARD` shaklini yaratadi (darsga tayyorgarlik, oʻqitish usuli, fan mazmuni, baholash hamda oʻquv sharoitlari va jihozlar boʻyicha har biridan 3 tadan savol, 5 ballik shkalada, shuningdek 1 ta fikr savoli).
2. **Semestrni sozlash**: semestr, shakl, minimal javoblar soni, minimal javob berish ulushi (%). Standart qiymatlar **Sozlamalar > Fan soʻrovnomasi** dan olinadi (5 ta javob, 25%). Natijalar koʻrinishi uchun ikkala chegara ham bajarilishi kerak. Javoblar soni anonimlikni himoya qiladi (javoblar juda kam boʻlsa, talabalarni taxmin qilish mumkin); javob berish ulushi natijalarning reprezentativligini taʼminlaydi.
3. **Soʻrovnoma muddati**: semestrni tahrirlash ekranidagi **jarayon muddatlari** orasiga har bir mashgʻulotlar davri uchun **Fan soʻrovnomasi** muddatini qoʻshing ([10-bob](10-terms.md)). Maqsadli mezonlar kurslar boʻyicha alohida muddatlar belgilash imkonini beradi.
4. Muddat davomida `uv run manage.py evaluation_remind {term}` soʻrovnomani tugatmagan talabalarga eslatma xatlarini yuboradi (`--dry-run` faqat ularni sanaydi). Javob berish ulushini **Fan guruhlari boʻyicha javoblar** boʻlimida koʻring.
5. Baholarni qayta ishlash tugagach, **Natijalarni eʼlon qilish** (yoki `uv run manage.py evaluation_publish_results {term}`). Buyruqlar [buyruqlar](../operations/commands.md) boʻlimida tasvirlangan.

## Shakllar va savollar

| Maydon | Tavsif |
|---|---|
| Kod, Nomi, Tavsif | Tavsif talabaning soʻrovnoma ekrani yuqorisida koʻrsatiladi |
| Shkala ballari | 2 dan 10 gacha, odatda 5 |
| 1 ning yozuvi, Eng yuqori ball yozuvi | Masalan, Mutlaqo qoʻshilmayman, Toʻliq qoʻshilaman |

**Savollar** yorligʻi: yoʻnalish (bir yoʻnalishdagi savollar guruhlanadi), savol, tur (Shkala, Fikr), majburiy, **Teskari** (salbiy ifodalangan savol; oʻrtacha qiymatlarda javob teskari hisoblanadi, masalan "Dars surʼatiga ergashish qiyin edi" savoliga berilgan 5 ball 1 sifatida hisoblanadi), tartib.

Kamida bitta javobga ega shaklning savollari yoki shkalasini endi oʻzgartirib boʻlmaydi (natijalar hech qachon berilmagan savolga javobga aylanib qolmasligi uchun). Uni oʻzgartirish uchun **Shaklni nusxalash** bilan yangi shakl yarating va undan keyingi semestrda foydalaning.

## Nima baholanadi

- Semestr soʻrovnomasi sozlangan semestrda yozilgan yoki yakunlangan fanlar. Voz kechilgan va chiqarilgan fanlar hisobga olinmaydi.
- **Fan soʻrovnomasi** sozlamasi oʻchiq fanlar hisobga olinmaydi (amaliyotlar, stajirovkalar va shu kabilar; [17-bob](17-courses-and-curriculum.md)).
- Fanni faqat uning mashgʻulotlar davrining fan soʻrovnomasi muddati talaba uchun ochiq boʻlgan paytda baholash mumkin.

## Talaba ekrani

Portaldagi **Fan soʻrovnomasi**: baholanadigan fanlar roʻyxatida **Baholash** tugmasini bosing, savollarga javob bering va yuboring. Barcha majburiy savollarga javob berilishi kerak, yuborilgan javobni oʻzgartirib boʻlmaydi. Har bir fan bir marta baholanadi.

**Baholarni koʻrishni toʻsish** (sozlama, standart holatda yoqilgan): muddat davomida semestrda baholanmagan fani bor talabadan shu semestr baholari portaldagi baholar ekranida va baholar hisobotida xabar bilan yashiriladi. Soʻrovnoma tugatilgach yoki muddat tugagach baholar koʻrinadi. Boshqa semestrlarning baholari koʻrinib turaveradi.

## Natijalar

- Oʻqituvchilar: portaldagi **Mening darslarim** boʻlimidagi **Fan soʻrovnomasi natijalari**. Faqat semestr natijalari eʼlon qilingandan keyin ochiladi.
- Xodimlar: **Fan soʻrovnomasi > Fan guruhlari boʻyicha javoblar** har bir fan guruhi uchun javoblar soni va ulushini koʻrsatadi; **Natijalar** natijalar ekranini ochadi. Batafsil natijalar xodimlarga ham faqat eʼlon qilingandan keyin koʻrsatiladi (muddat davomida natijalardagi oʻzgarishlarni yakunlash vaqtlari bilan solishtirish orqali talabalarni aniqlash mumkin boʻlardi).
- Natijalar ekrani: javoblar/kutilgan (javob berish ulushi), har bir savol boʻyicha oʻrtacha qiymat va har bir ball boʻyicha javoblar soni (teskari savollar uchun teskari), umumiy oʻrtacha, fikrlar (tasodifiy tartibda).
- Javoblar soni minimaldan kam yoki javob berish ulushi minimaldan past boʻlgan fan guruhida natijalar va fikrlar emas, faqat javoblar soni koʻrsatiladi.

## Sozlamalar

**Sozlamalar > Fan soʻrovnomasi**: semestr soʻrovnomasi tugaguncha uning baholarini yashirish (standart holatda yoqilgan), barcha savollarga bir xil javobni rad etish (standart holatda oʻchiq), yangi semestr soʻrovnomasi uchun minimal javoblar soni (standart: 5) va minimal javob berish ulushi (standart: 25%, eski oʻquv boʻlimi ekranidagi chegara).

## Ushbu oʻrnatmadagi ekranlar

Ekranlar va funksiyalar asl tizimnikidek (Filament, Livewire); ulardan foydalanish biroz farq qiladi.

- **Semestr soʻrovnomalari** roʻyxati ustidagi **Semestrni sozlash** kiritish ekranini ochadi (semestr, shakl, minimal javoblar soni, minimal javob berish ulushi). Boʻsh qoldirilgan chegara yangi semestr uchun sozlamaning standart qiymatini oladi, mavjud semestr uchun esa joriy qiymatni saqlaydi. Qator menyusidagi **Oʻzgartirish** xuddi shu ekranni ochadi (semestrni oʻzgartirib boʻlmaydi); javoblari bor semestr shaklini oʻzgartira olmaydi. Qator menyusidagi **Natijalarni eʼlon qilish** tasdiqlash ekranini ochadi. Qator menyusi eʼlon qilingan semestrlar uchun ham koʻrsatiladi; ular uchun natijalar allaqachon eʼlon qilingani haqida xabar chiqadi.
- **Soʻrovnoma shakllari** tahrirlash ekranida savollar **Savollar** yorligʻida qoʻshiladi, oʻzgartiriladi va oʻchiriladi. Javoblari bor shakl savollarini faqat koʻrish uchun koʻrsatadi va shkala ballari maydonini qulflaydi. Yuqoridagi **Shaklni nusxalash** yangi kod uchun ekran ochadi; nusxalangandan keyin yangi shaklning tahrirlash ekrani ochiladi.
- **Fan guruhlari boʻyicha javoblar** filtrlari: semestr (standart: fan soʻrovnomasi boʻlgan oxirgi semestr, barcha semestrlar uchun **Hammasi**), fan guruhini ochgan birlik. Qidiruv fan kodining boshlanishiga mos keladi. Qator menyusidagi **Natijalar** portaldagi natijalar ekranini (`/portal/sections/{section id}/evaluation/`) shu oynada ochadi.
- Portaldagi **Mening darslarim** jadvalining **Fan soʻrovnomasi natijalari** ustuni: semestr natijalari eʼlon qilingach **Natijalar** havolasi, aks holda **Eʼlon qilinmagan**.
- Talaba portalidagi **Fan soʻrovnomasi**: **Yuborish** brauzerda yana bir marta soʻraydi (JavaScript boʻlmasa, shakl bevosita yuboriladi). Majburiy savolga javob berilmagan boʻlsa, kiritilgan javoblar xato bilan qayta koʻrsatiladi. Baholar ekranidagi eslatma **Fan soʻrovnomasi** ga havola qiladi.
- Javoblarni saqlash: javob ID si tasodifiy UUID. Javoblar, javob qiymatlari va yakunlash yozuvlari talabaning fanga yozilganligi, muddat va takrorlar tekshirilgandan keyin tizim kontekstida bitta tranzaksiyada yoziladi va maʼlumot oʻzgarishi yozuviga (audit) yozilmaydi. Shakl qulflangan-qulflanmagani (javoblari borligi) ekranni ochgan shaxsning koʻrish qamrovidan qatʼi nazar aniqlanadi.

[Administrator qoʻllanmasi mundarijasi](README.md)
