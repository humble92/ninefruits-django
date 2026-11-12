# 21. Baholar

Menyu: **Baholar > Baholash jarayoni**, **Baholash usuli soʻrovlari**, **Baholarni oʻzgartirish**, **Semestr natijalari**, **Sozlamalar > Baholash siyosati**. Oʻqituvchilar portaldagi **Mening darslarim > Baholarni kiritish** dan foydalanadi.

| Ruxsat | Nimaga imkon beradi |
|---|---|
| `Baholar, baholash jarayoni va semestr natijalarini koʻrish` | Baholash jarayoni, semestr natijalari va talabalar baholar hisobotini koʻrish |
| `Baholarni yakunlash va qaytarish, oʻqituvchilar nomidan baho kiritish, semestrlarni yopish` | Fan guruhi baholarini yakunlash yoki qaytarish, oʻqituvchilar nomidan baho kiritish (muddatdan qatʼi nazar), baho chegaralaridan tashqari baholarni istisno sifatida topshirish, semestrlarni yopish, qayta hisoblash. Tashkiliy birlik qamrovi bilan tayinlanganda faqat shu boʻlinma ochgan fan guruhlari |
| `Xodimlar baho chegaralaridan tashqari baho topshirganda xabar olish (kafedra mudirlari, oʻquv boʻlimi)` | Istisno sifatida topshirish haqida xabarnomalar olish. Kafedra mudirlari va oʻquv boʻlimi rahbariga tashkiliy birlik qamrovi bilan tayinlanadi |
| `Yakunlangan bahoni oʻzgartirishni soʻrash` | Oʻzi dars bermaydigan fan guruhlari uchun oʻzgartirish soʻrash (masalan, akademik halollik buzilishi uchun bahoni bekor qilish) |
| `Baho oʻzgarishlarini tasdiqlash yoki rad etish (oʻz soʻrovlaringizdan tashqari)` | Bahoni oʻzgartirish soʻrovlari boʻyicha qaror qabul qilish |
| `GPA, qayta oʻqish, akademik holat va imtiyozlar siyosatini boshqarish` | Baholash siyosati sozlamalari |

Oʻqituvchilar oʻz fan guruhlari uchun hech qanday ruxsatsiz baho kiritadi va oʻzgartirish soʻraydi. Rollar boʻyicha standart sozlamalar: Registratorda koʻrish, yakunlash, tasdiqlash va istisnolarni koʻrib chiqish; Oʻquv-uslubiy boshqarmada koʻrish, oʻzgartirish soʻrash va siyosat; Maʼlumotnomalar masʼuli va Kafedra yordamchisida koʻrish ruxsati bor. Baholash usuli soʻrovlari `Fan guruhlarini rejalashtirish (oʻqituvchilar, vaqtlar, auditoriyalar)` ruxsati bilan hal qilinadi.

## Eski tizimdan farqlari

- Eski tizimda (YUSTIC) oʻqituvchi saqlagan baho darhol yakuniy boʻlardi, oʻquv boʻlimi esa uni ekranda bevosita tahrirlardi. Sabab ham, tasdiqlash bosqichi ham yoʻq edi, baʼzi hisoblar tomonidan qilingan tahrirlar hatto zaxira yozuvlarida ham koʻrinmasdi. Yangi tizimda **kiritish → topshirish → yakunlash** bosqichlari mavjud, yakunlangan baho esa faqat **oʻzgartirish soʻrovini boshqa shaxs tasdiqlaganda** oʻzgaradi. Buni ham ilova, ham maʼlumotlar bazasi (triggerlar) taʼminlaydi.
- Eski tizimda oʻqituvchi soʻrovni manipulyatsiya qilib, oʻzi dars bermaydigan fan guruhlariga baho saqlay olardi. Yangi tizim tayinlangan oʻqituvchilarni va ruxsat qamrovini serverda hamda maʼlumotlar bazasida tekshiradi.
- GPA, akademik ogohlantirishlar va imtiyozlar har bir ekranda darhol hisoblanmaydi; ular **semestr natijalari** sifatida saqlanadi. Semestr yopilganda ular shu semestrning rasmiy yozuviga aylanadi.
- Qayta oʻqish oldingi bahoni umumiy GPA dan faqat **yangi baho yakunlangandan keyin** chiqaradi (eski tizim uni fanga yozilishda chiqarardi va fan guruhi bekor qilinganda buni qaytarmasdi).
- Eski tizim faqat baholar menyusini oʻchirib qoʻyardi; baholar manzil orqali koʻrinib qolardi. Yangi tizim baholarni koʻrishni toʻsishni serverda taʼminlaydi.

## Semestr tartibi

1. **Jarayon muddatlari** ([10-bob](10-terms.md)): har bir mashgʻulotlar davri uchun **Baho kiritish** muddati. Oʻqituvchilar faqat shu muddat ichida baho kiritadi va topshiradi.
2. Oʻqituvchilar baholarni kiritadi va topshiradi. `uv run manage.py grades_remind_missing {term}` topshirmagan oʻqituvchilarga eslatma xatlarini yuboradi.
3. **Baholash jarayoni** da har bir fan guruhini yakunlang yoki oʻqituvchiga qaytaring.
4. Barcha fan guruhlari yakunlangach, **Semestr natijalari > Semestrni yopish**. Semestr natijalari, akademik holat va imtiyozlar belgilanadi va semestr **Baholar yopilgan** holatiga oʻtadi.
5. Shundan keyin oʻzgartiriladigan baholar **Baholarni oʻzgartirish** orqali amalga oshiriladi.

## Baholash shkalasi va baholash usuli

**Baholash shkalasi oʻrnatishda belgilanadi va uni oʻzgartirib boʻlmaydi** (2026-10-23 dagi qaror), chunki barcha baholar va GPA shu shkalada. Uni `uv run manage.py setup_install --grade-scale=4.5|4.3` bilan belgilang; aks holda birinchi profilning shkalasi ishlatiladi (Koreya universiteti 4.5, eski YUST 4.3). Asosiy maʼlumotlar > Baholash shkalalari boʻlimidagi **Standart** belgisini koʻchirib boʻlmaydi va standart shkalani oʻchirib boʻlmaydi. Har bir bahoning **ball oraliqlari** (quyi va yuqori %) va baho bali shu ekranda tahrirlanadi ([11-bob](11-course-categories-and-grade-scales.md)).

Har bir fan guruhida **baholash usuli** bor. Standart usul — **Mutlaq baholash**.

| Baholash usuli | Oʻqituvchi kiritadi | Saqlanadi | Topshirish sharti |
|---|---|---|---|
| Mutlaq baholash (standart) | Har bir talaba uchun **ball (0–100)**. Baho ball oraligʻidan kelib chiqadi va uni tanlab boʻlmaydi (faqat ballsiz baholar, masalan I, bevosita tanlanadi) | Ball (asl qiymat), baho, baho bali | Har bir talabaga baho |
| Nisbiy baholash | Har bir talaba uchun **baho**. Ball kiritilmaydi (kiritilsa, rad etiladi) | Baho, baho bali | Har bir talabaga baho + **baho chegaralari**ga rioya qilingan |
| Oʻtdi/oʻtmadi fani | Baholash usulidan qatʼi nazar P/NP | Baho | Har bir talabaga baho |

- Nisbiy baholashni xohlagan oʻqituvchi baho kiritish ekranida **Nisbiy baholash ni soʻrash** tugmasini bosadi (sabab bilan). Guruhni ochgan boʻlinma uchun `Fan guruhlarini rejalashtirish (oʻqituvchilar, vaqtlar, auditoriyalar)` ruxsatiga ega xodim (kafedra yordamchisi, oʻquv-uslubiy boshqarma) uni **Baholar > Baholash usuli soʻrovlari** boʻlimida tasdiqlaydi yoki rad etadi (izoh majburiy), oʻqituvchiga esa e-pochta orqali xabar beriladi. Tasdiqlanganda eski usulda kiritilgan qoralama baholar tozalanadi. Baholar **topshirilgan**dan keyin soʻrov ham, oʻzgartirish ham mumkin emas. Xodimlar usulni fan guruhi ekranida ham oʻzgartira oladi, lekin faqat baholar kiritilgunga qadar.
- Qayta oʻqish uchun eng yuqori baho: mutlaq baholashda chegaradan yuqori baho beradigan ball **chegara bahosigacha tushiriladi** (ball oʻzgarmaydi). Nisbiy baholashda chegaradan yuqori bahoni tanlab boʻlmaydi.

## Baho chegaralari (nisbiy baholash)

**Sozlamalar > Baholash siyosati > Nisbiy baholash**: har bir baho guruhi uchun chegara (standart: A guruhi 30%, B guruhi 40%), chegaradan yuqori ruxsat etilgan ogʻish (standart: 1 foiz punkti), tekshirish uchun baholangan talabalarning minimal soni (standart: 10).

- Baho guruhlari harf boʻyicha: A+, A0 va A- A guruhini; B+, B0 va B- B guruhini tashkil qiladi. Chegarasi yoʻq guruhlar (C, D, F) cheklanmagan.
- Maxraj — fan guruhida GPA ga hisoblanadigan bahoga ega talabalar soni. Voz kechgan talabalar va P/NP/I hisobga olinmaydi.
- Talabalar soni minimaldan kam fan guruhlari tekshirilmaydi (7 talabadan 30% A ni bajarib boʻlmaydi).
- Oʻqituvchilar baho kiritish ekranidagi **Baho chegaralarini tekshirish** orqali joriy taqsimotni chegaralar bilan solishtirib koʻradi va chegaralardan yuqori boʻlsa **topshira olmaydi**.
- Baholarni boshqarish ruxsatiga ega xodimlar chegaralardan yuqori baholarni topshira oladi, biroq **istisno sifatida topshirish** tarzida: sabab majburiy, taqsimot va sabab faoliyat jurnalida qayd etiladi, `Xodimlar baho chegaralaridan tashqari baho topshirganda xabar olish (kafedra mudirlari, oʻquv boʻlimi)` ruxsatiga ega xodimlar (kafedra mudirlari, oʻquv boʻlimi rahbari, tashkiliy birlik qamrovi bilan tayinlangan) e-pochta xatini oladi va fan guruhi **Istisno sifatida topshirilgan** deb belgilanadi. **Baholash jarayoni** ni faqat istisno sifatida topshirilganlar boʻyicha filtrlash mumkin.

## Baho kiritish (oʻqituvchilar)

Portaldagi **Mening darslarim** boʻlimida fan guruhining **Baholarni kiritish** sahifasini oching. Ekranning yuqori qismida fan guruhining baholash usuli, kiritish boʻyicha koʻrsatmalar va baholash usuli soʻrovi koʻrsatiladi.

- Mutlaq baholash: ball kiritilishi bilanoq baho paydo boʻladi.
- Nisbiy baholash: faqat baho tanlanadi. Ball ustuni yoʻq. Chegaralarni **Baho chegaralarini tekshirish** bilan tekshiring va topshiring.
- Baholar roʻyxati fanning baholash turiga bogʻliq. Harfli baholanadigan fanlarda harfli baholar, oʻtdi/oʻtmadi fanlarida P/NP koʻrsatiladi ([11-bob](11-course-categories-and-grade-scales.md)).
- **Qoralamani saqlash** istalgan vaqtda mumkin. Talabalar qoralama baholarni koʻrmaydi.
- **Baholarni topshirish** uchun har bir talabaga baho qoʻyilgan boʻlishi kerak. Topshirilgandan keyin oʻqituvchi ularni oʻzgartira olmaydi. Notoʻgʻri baho boʻlsa, yakunlashdan oldin oʻquv boʻlimidan baholarni qaytarishni soʻrang yoki yakunlangandan keyin oʻzgartirish soʻrang.
- Voz kechgan talabalar W sifatida koʻrsatiladi va baho olmaydi.

## Yakunlash va qaytarish (oʻquv boʻlimi)

**Baholash jarayoni**: semestrning fan guruhlari topshirilmagan, topshirilgan va yakunlangan baholar soni bilan. **Yakunlashga tayyor** filtri faqat barcha talabalarning baholari topshirilgan fan guruhlarini koʻrsatadi.

- **Yakunlash**: topshirilgan baholarni yakunlaydi. Fanlarga yozilishlar **Yakunlangan** holatiga oʻtadi va talabalar oʻz baholarini koʻradi. Talabalarning semestr natijalari qayta hisoblanadi. Bir nechta fan guruhini tanlab, **Tanlanganlarni yakunlash** bilan yakunlash mumkin. Hali bahosi topshirilmagan talabasi bor fan guruhlari oʻtkazib yuboriladi.
- **Oʻqituvchiga qaytarish**: sabab koʻrsatib topshirishni bekor qiladi. Baholar qoralamaga qaytadi va oʻqituvchi e-pochta xatini oladi.
- **Baholar**: baho kiritish ekranini ochadi. Oʻquv boʻlimi yakunlashdan oldin muddatdan qatʼi nazar baholarni kiritishi yoki oʻzgartirishi mumkin. Xodim oʻqituvchi **topshirgan** bahoni oʻzgartirsa, eski va yangi qiymatlar `grades.submitted_changed` audit hodisasida qayd etiladi.

## Baholarni oʻzgartirish

Yakunlangan bahoni oʻzgartirishning yagona yoʻli.

1. Soʻrov: oʻqituvchi baho kiritish ekranida talaba uchun **Oʻzgartirishni soʻrash** tugmasini bosadi (sabab bilan; mutlaq baholashda yangi ball, nisbiy baholashda yangi baho). Qayta oʻqish chegarasi oʻzgartirishlarga ham qoʻllaniladi. Oʻzi dars bermaydigan fan guruhlari uchun `Yakunlangan bahoni oʻzgartirishni soʻrash` ruxsatiga ega xodimlar xuddi shu ekranda soʻrov beradi. Har bir baho uchun faqat bitta ochiq soʻrov boʻlishi mumkin.
2. Qaror: **Baholar > Baholarni oʻzgartirish** boʻlimida (standart: koʻrib chiqilayotganlar roʻyxati; menyuda koʻrib chiqilayotganlar soni koʻrsatiladi) **Tasdiqlash** yoki **Rad etish** tugmasini bosing (izoh majburiy). Soʻrov beruvchi oʻz soʻrovi boʻyicha qaror qabul qila olmaydi (buni maʼlumotlar bazasi cheklovi ham taʼminlaydi).
3. Tasdiqlanganda baho (mutlaq baholashda ball va baho) darhol oʻzgaradi, talabaning semestr natijasi va keyingi semestrlarning umumiy GPA si qayta hisoblanadi. Akademik holat va imtiyozlar semestr yopilganda belgilangan qiymatlarini saqlab qoladi.

Soʻrov beruvchi soʻrov koʻrib chiqilayotgan paytda **Soʻrovni bekor qilish** mumkin. Har bir soʻrov va qaror faoliyat jurnalida sababi bilan qayd etiladi.

## GPA hisoblash

| Band | Qoida |
|---|---|
| Olingan kreditlar | Har bir yakunlangan fan (F, P, NP, I ni ham qoʻshib) |
| Toʻplangan kreditlar | Oʻtish baholari (F, NP, I dan tashqari) |
| GPA kreditlari | GPA ga kiritiladigan baholar. F 0 ball bilan hisoblanadi; P/NP/I chiqarib tashlanadi |
| GPA | Yigʻindi (baho bali × kreditlar) ÷ GPA kreditlari. Faqat oʻtdi/oʻtmadi fanlaridan iborat semestrda GPA boʻlmaydi |
| Kasr xonalari | Kasr xonalari va yaxlitlash (matematik yaxlitlash, tashlab yuborish) siyosatdan olinadi. Butun sonli arifmetika ishlatiladi, shuning uchun chegaralarda xatolik boʻlmaydi (masalan 3.4375 → 3.438) |
| Semestr GPA | Shu semestrning barcha baholari (qayta oʻqish bilan almashtirilgan oldingi baho ham oʻz semestri GPA sida hisoblanaveradi) |
| Umumiy GPA | Qayta oʻqilgan fan siyosatga koʻra faqat bir marta hisoblanadi: **Oxirgi urinish** (standart; yomonroq boʻlsa ham oxirgisi) yoki **Eng yaxshi urinish**. Almashtirilgan baho umumiy kreditlarga ham kiritilmaydi va baholar ekranida "umumiy GPA da qayta oʻqish bilan almashtirilgan" sifatida koʻrsatiladi |

Qayta oʻqish bogʻlanishi fanga yozilishda belgilanadi ([20-bob](20-registration.md)): xuddi shu fan yoki muqobil fanni qayta oʻqish uni oldingi fanga yozilish bilan bogʻlaydi.

## Akademik holat va imtiyozlar (semestrni yopish)

| Siyosat | Standart | Eski YUST profili |
|---|---|---|
| Ogohlantirish chegarasi | Semestr GPA si 1.75 dan past | 1.3 dan past |
| Faqat asosiy semestrlarni hisobga olish | Ha | Ha |
| Chetlashtirishni koʻrib chiqish uchun ogohlantirishlar soni | 0 (oʻchiq) | 4 |
| Faqat ketma-ket ogohlantirishlarni hisoblash | Yoʻq (umumiy son) | Yoʻq |
| Imtiyoz uchun minimal GPA, minimal GPA kreditlari | 4.0, 15 kredit | 0, 0 (eski tizim shunchaki eng yaxshi N talabani olardi) |
| Oʻzlashtirilmagan fan boʻlsa imtiyoz berilmaydi | Ha | Yoʻq |
| GPA kasr xonalari | 2, matematik yaxlitlash | 3, matematik yaxlitlash |
| Baholash shkalasi (oʻrnatishda belgilangan) | 4.5 (KR45) | 4.3 (YUST43) |
| Baho chegaralari (nisbiy baholash) | A 30%, B 40%, ogʻish 1 foiz punkti, 10 talabadan boshlab tekshiriladi | Xuddi shunday |

- **Akademik ogohlantirish**: semestr GPA si chegaradan **past**. Faqat oʻtdi/oʻtmadi fanlaridan iborat semestr ogohlantirish bermaydi.
- **Chetlashtirishni koʻrib chiqish**: ogohlantirishlar soni chegaraga yetganda belgilanadi. Oʻqishdan chetlashtirishning oʻzi maqom oʻzgarishi hisoblanadi ([13-bob](13-status-changes-and-advisors.md)).
- Faqat asosiy semestrlar hisobga olinganda yozgi va qishki semestrlarda akademik holat boʻlmaydi va ular ketma-ket ogohlantirishlar zanjirini uzmaydi.
- **Imtiyozlar (aʼlochilar)**: mezonlarga javob beradigan talabalar har bir dastur boʻyicha semestr GPA si asosida reytingga qoʻyiladi (teng natijalar bir xil oʻrinni egallaydi; keyingi oʻrin tashlab ketiladi).
- Talaba yozuvidagi **Akademik holat** eng soʻnggi natijaga oʻzgaradi. Jarayon muddatlari va fan guruhi shartlaridagi "akademik holat" mezoni shu qiymatdan foydalanadi.

**Semestr natijalari** ekranida akademik ogohlantirish olgan talabalar roʻyxati va aʼlochilar roʻyxatini (eski tizimdagi ogohlantirish va imtiyozlar hisobotlari) koʻrish uchun semestr, akademik holat, imtiyozlar va dastur boʻyicha filtrlang. Avval yakunlanmagan fan guruhlarini koʻrish uchun **Semestrni yopish** ni **Faqat oldindan koʻrish** (standart) bilan ishga tushiring, soʻngra uni oʻchirib, qayta ishga tushiring. **Qayta hisoblash** oʻzgartirilgan siyosatni oʻtgan semestrlar natijalariga qoʻllaydi (sabab majburiy).

## Talaba ekrani va baholar hisoboti

Xodim talabaning baholar hisobotini ochganda bu `transcript.viewed` audit hodisasida (talaba raqami bilan) qayd etiladi.

- Portaldagi **Baholar**: semestrlar boʻyicha yakunlangan baholar (voz kechishlar W sifatida), semestr GPA si va toʻplangan kreditlar, umumiy GPA, akademik holat, imtiyozlar. Bitiruvchilar ham koʻra oladi. Yakunlanmagan baholar koʻrsatilmaydi.
- **Chop etish**, **PDF**: tekshirish uchun norasmiy baholar hisoboti. PDF Gotenberg yordamida yaratiladi. Rasmiy akademik maʼlumotnoma maʼlumotnoma sifatida beriladi ([23-bob](23-certificates.md)). Xodimlar talabaning baholar hisobotini talaba yozuvi ekranidagi yoki Semestr natijalaridagi **Baholar hisoboti** orqali ochadi (`Baholar, baholash jarayoni va semestr natijalarini koʻrish` ruxsati).
- **Cheklov** da **Baholarni koʻrishni toʻsadi** yoqilgan talaba baholar ekranini yoki baholar hisobotini koʻra olmaydi ([20-bob](20-registration.md)).
- Fan soʻrovnomasi muddati davomida semestrdagi fan soʻrovnomasini tugatmagan talabadan shu semestr baholari yashiriladi (sozlama, [22-bob](22-course-evaluation.md)).

## Baholash siyosati

**Sozlamalar > Baholash siyosati** (`GPA, qayta oʻqish, akademik holat va imtiyozlar siyosatini boshqarish` ruxsati). Yuqoridagi jadval bandlarini oʻzgartiradi. Oʻzgartirilgan siyosat keyingi hisoblashdan boshlab qoʻllaniladi. Uni oʻtgan semestrlar natijalariga qoʻllash uchun **Qayta hisoblash** dan foydalaning. Akademik holat va imtiyozlar semestr yopilganda belgilanadi, shuning uchun ular yopilgan semestrga qayta qoʻllanilmaydi.

## Ushbu oʻrnatmadagi ekranlar

Ekranlar va funksiyalar asl tizimnikidek (Filament, Livewire); ulardan foydalanish biroz farq qiladi.

- **Baholash jarayoni** qator menyusi: **Baholar** (portaldagi baho kiritish ekrani), **Yakunlash** (tasdiqlash ekrani), **Oʻqituvchiga qaytarish** (sabab ekrani). Bir nechta fan guruhini yakunlash uchun ularni roʻyxatda tanlang va amallar roʻyxatidan **Tanlanganlarni yakunlash** ni tanlang. Filtrlar: semestr (standart: joriy semestr, barcha semestrlar uchun **Hammasi**), fan guruhini ochgan birlik, istisno sifatida topshirilgan, yakunlashga tayyor.
- **Baholarni oʻzgartirish** va **Baholash usuli soʻrovlari** qator menyusidagi **Tasdiqlash** va **Rad etish** izoh uchun ekran ochadi. Standart roʻyxat kutilayotgan soʻrovlarni koʻrsatadi, menyu esa nechta soʻrov kutilayotganini koʻrsatadi.
- **Semestr natijalari** roʻyxati ustidagi **Semestrni yopish**: semestr, **Faqat oldindan koʻrish** (standart holatda yoqilgan), sabab. Oldindan koʻrish semestrni yopish mumkinligini va yakunlanmagan fan guruhlarini (30 tagacha) xabarlarda koʻrsatadi. Boshlangan yopish har biri 100 talabadan iborat navbat vazifalari (Celery) sifatida bajariladi; bajarilayotgan yopish jarayoni semestr natijalari roʻyxati ustida koʻrsatiladi. Tugagach, semestr **Baholar yopilgan** holatiga oʻtadi va uni boshlagan xodim e-pochta xatini oladi. Biror vazifa bajarilmasa, yopish tugamaydi va semestr oʻz holatida qoladi; sababini bartaraf eting va qayta yoping (natija bir xil boʻladi). Buyruqlar qatoridan: `uv run manage.py term_close {term} --dry-run`, `uv run manage.py term_close {term} --reason=...` ([buyruqlar](../operations/commands.md)).
- **Baholash siyosati** da baho chegaralarini vergul bilan ajratilgan harf va foizlar koʻrinishida yozing, masalan `A=30, B=40`. Boʻsh boʻlsa, chegara yoʻq.
- Portalda baho kiritish: mutlaq baholashda baho ball yozilgandan keyin tez orada uning yonida paydo boʻladi. **Qoralamani saqlash**, **Baho chegaralarini tekshirish** va **Baholarni topshirish** ekranning pastki qismida joylashgan; saqlash bajarilmasa (masalan, ball oraliqdan tashqarida), kiritilgan qiymatlar xato bilan birga qayta koʻrsatiladi. Talaba qatoridagi **Oʻzgartirishni soʻrash** jadval ostida soʻrov maydonlarini ochadi.
- Xodimlar uchun baholar hisoboti manzili: `/student-records/{student record id}/transcript/` (talaba yozuvi ekranidagi **Baholar hisoboti** tugmasi, semestr natijasi qatoridagi **Baholar hisoboti**). PDF uchun `?format=pdf` qoʻshing.
- LMS ga bogʻlangan fan guruhi uchun baho kiritish ekrani LMS ballarini qoralama sifatida yuklashi mumkin ([28-bob](28-lms-integration.md)). Fan soʻrovnomasi ochiq va tugallanmagan semestr baholari eslatma va **Fan soʻrovnomasi** havolasi bilan yashiriladi ([22-bob](22-course-evaluation.md)).

[Administrator qoʻllanmasi mundarijasi](README.md)
