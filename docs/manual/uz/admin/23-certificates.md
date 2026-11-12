# 23. Maʼlumotnomalar

Menyu: **Maʼlumotnomalar > Berilgan maʼlumotnomalar**, **Maʼlumotnomalar > Maʼlumotnoma turlari**, **Sozlamalar > Maʼlumotnoma sozlamalari**. Maʼlumotnomalar talaba yozuvi ekranidagi **Maʼlumotnoma berish** tugmasi orqali beriladi (**Talabalar va xodimlar > Talaba yozuvlari**, yozuvni oching). Talabalar oʻz maʼlumotnomalarining PDF fayllarini portaldagi **Maʼlumotnomalar** boʻlimidan yuklab oladi. Har kim maʼlumotnomani `/verify/{code}/` sahifasida tekshirishi mumkin.

| Ruxsat | Nimaga imkon beradi |
|---|---|
| `Maʼlumotnomalarni berish, qayta yaratish va bekor qilish` | Berish, qayta yaratish, bekor qilish, berilgan maʼlumotnomalarni koʻrish (talaba yozuvlarini koʻrish qamrovi doirasida) |
| `Maʼlumotnoma turlari, shablonlari va sozlamalarini boshqarish` | Turlar va ularning har bir til uchun shablonlari, seriya raqami shabloni, imzolovchilar |

Rollar boʻyicha standart sozlamalar: Maʼlumotnomalar masʼuli maʼlumotnoma beradi, Registratorda ikkalasi ham bor, Oʻquv-uslubiy boshqarma turlar va shablonlarni boshqaradi. Berish ruxsatini **umumiy qamrov** bilan bering (maʼlumotlar bazasi siyosati faqat umumiy tayinlashni qabul qiladi); xodim qaysi talabalar uchun maʼlumotnoma bera olishi uning talaba yozuvlarini koʻrish qamroviga bogʻliq. Masalan, fakultetning maʼlumotnomalar masʼuliga `Maʼlumotnomalarni berish, qayta yaratish va bekor qilish` ruxsatini umumiy qamrovda, `Talaba yozuvlarini koʻrish` ruxsatini esa shu fakultet qamrovida bering.

## Eski tizimdan farqlari

- **Berilgan maʼlumotnomalar reyestri.** Eski tizim (YUSTIC) toʻgʻridan-toʻgʻri ekrandan chop etardi (`aca3/cti_*`), uning reyestri (`SRCERT`) esa faqat raqam yaratish uchun mavjud edi, shuning uchun maʼlumotnomani kim bergani yoki u bekor qilinganligi koʻrinmasdi. Yangi tizim har bir berish uchun seriya raqami, tekshirish kodi, xodim, maqsad, nusxalar soni, PDF fayl va nazorat summasini qayd etadi, bekor qilingan maʼlumotnoma esa oʻz qatorini saqlab qoladi.
- **Tekshirish.** Eski tizimda bu yoʻq edi. Har bir maʼlumotnomada tekshirish kodi va QR kod bor, ommaviy sahifa esa maʼlumotnoma berilganligi, uning turi, berilgan sanasi va niqoblangan egasini (ismning birinchi va oxirgi belgisi, talaba raqamining birinchi 4 ta belgisi) koʻrsatadi.
- **Shablonlar.** Eski tizimda har bir tur va til uchun alohida PDF skript bor edi. Yangi tizim har bir tur uchun har bir tildagi shablonni (sarlavha, matn, pastki qism, imzolovchi) ekranda tahrirlaydi.
- **Toʻsishlar.** Eski tizim fanlarga yozilishni rad etish roʻyxatidan qatʼi nazar maʼlumotnoma berardi. Yangi tizim maʼlumotnomalari toʻsilgan talabaga maʼlumotnoma bermaydi ([20-bob](20-registration.md)).
- Toʻlovlar qayd etilmaydi (eski tizim faqat summani qayd etardi).
- Talabalar tomonidan onlayn soʻrov yoʻq (koʻchirish rejasi 17.5). Maʼlumotnomalarni xodimlar beradi.

## Turlar va shablonlar

**Maʼlumotnoma turlari**: kod (seriya raqamida ishlatiladi), nomi (har bir til uchun), kim uchun (har qanday talaba yozuvi / talabalar (bitirmagan) / bitiruvchilar), baholarni oʻz ichiga oladi, suratni oʻz ichiga oladi, faol, tartib. Koreya universiteti profili (`setup_install --profile=korean-university`) toʻrt tildagi (koreys, ingliz, soddalashtirilgan xitoy, lao) shablonlari bilan uchta tur yaratadi. Biror tur mavjud boʻlsa, u hech narsa qoʻshmaydi, shuning uchun siz kiritgan oʻzgarishlar saqlanib qoladi.

| Kod | Tur | Kim uchun | Izoh |
|---|---|---|---|
| `ENR` | Talabalik haqida maʼlumotnoma | Talabalar (bitirmagan) | |
| `GRD` | Bitirganlik haqida maʼlumotnoma | Bitiruvchilar | Bitirish sanasi, diplom raqami |
| `TRN` | Akademik maʼlumotnoma | Har qanday talaba yozuvi | Semestrlar boʻyicha yakunlangan baholar jadvali, umumiy GPA va toʻplangan kreditlar |

**Shablonlar** (tur tahrirlash ekranining pastki qismidagi **Shablonlar** boʻlimi): har bir til uchun bittadan. Til, sarlavha, matn (xatboshilar boʻsh qator bilan ajratiladi), pastki qism, imzolovchi. Matnda jingalak qavslardagi oʻrinbosarlar ishlatiladi.

| Oʻrinbosar | Qiymat |
|---|---|
| `{institution}` | Muassasa nomi (shu tilda) |
| `{student_name}`, `{student_number}` | Ism (shu tildagi shaklda, aks holda lotincha yozilishi), talaba raqami |
| `{program}`, `{org_unit}` | Taʼlim dasturi, tashkiliy birlik |
| `{admission_date}`, `{graduation_date}`, `{degree_number}` | Qabul sanasi, bitirish sanasi, diplom raqami |
| `{status}`, `{year_level}` | Talaba holati, kurs |
| `{birth_date}`, `{gender}`, `{nationality}` | Tugʻilgan sana, jinsi, fuqaroligi |
| `{issue_date}`, `{serial_number}`, `{purpose}`, `{copies}` | Berilgan sana, seriya raqami, maqsad, nusxalar soni |

Sanalar shu tilning formatida chop etiladi (masalan, `October 24, 2026`, `2026년 10월 24일`). Mavjud boʻlmagan qiymat (masalan, bitirish sanasi) boʻsh holda chop etiladi; roʻyxatda yoʻq oʻrinbosar yozilganicha qoladi. Matn ustiga shaxsiy maʼlumotlar jadvali (ism, talaba raqami, tugʻilgan sana, jinsi, fuqaroligi, taʼlim dasturi, qabul sanasi, soʻngra bitiruvchilar uchun bitirish sanasi, aks holda holat va kurs) avtomatik qoʻshiladi. Butun maʼlumotnoma (jadval sarlavhalari, sanalar, holat) shablon tilida chop etiladi.

## Sozlamalar

**Sozlamalar > Maʼlumotnoma sozlamalari** (`Maʼlumotnoma turlari, shablonlari va sozlamalarini boshqarish`)

- **Seriya raqami shabloni**: standart `{TYPE}-{YYYY}-{SEQ:6}` → `ENR-2026-000001`. Belgilar: `{TYPE}` (tur kodi), `{YYYY}` va `{YY}` (berilgan yil, muassasa vaqt mintaqasida) hamda `{SEQ:n}` (n xonali tartib raqami). Aynan bitta `{SEQ:n}` majburiy va undan keyin faqat oddiy matn kelishi mumkin. Ketma-ketlik har bir alohida prefiks uchun alohida hisoblanadi: `{TYPE}-{SEQ:6}` yillar oraligʻida har bir tur boʻyicha, `{YYYY}{SEQ:5}` turlar oraligʻida har bir yil boʻyicha hisoblaydi. Bir vaqtda berilgan maʼlumotnomalar hech qachon toʻqnashmaydi (hisoblagich maʼlumotlar bazasida atomar tarzda oshiriladi).
- **Tekshirishning amal qilish muddati (kun)**: 0 doimiy degani. Muddat oʻtgach, tekshirish sahifasi "muddati oʻtgan" deb javob beradi. Berish yozuvining oʻzi reyestrda qoladi.
- **Tillar boʻyicha imzolovchi**: muhr ustida chop etiladigan nom ("Rektor, Ninefruits universiteti"), muassasa qoʻllab-quvvatlaydigan har bir til uchun bitta maydon. Shablondagi imzolovchi ustuvor hisoblanadi.

## Maʼlumotnoma berish

Talaba yozuvi ekranidagi **Maʼlumotnoma berish**: tur (faollari), til (muassasa tillari), maqsad, nusxalar (1 dan 20 gacha). **Maʼlumotnoma berish** PDF ni yaratib saqlaydi va talaba yozuviga qaytaradi; xabarda seriya raqami **PDF** havolasi bilan koʻrsatiladi.

Quyidagi hollarda berish rad etiladi (ekran sababini koʻrsatadi):

- turning kim uchunligi mos kelmasa (bitiruvchiga talabalik haqida maʼlumotnoma, amaldagi talabaga bitirganlik haqida maʼlumotnoma)
- tur faol boʻlmasa
- shu til uchun shablon boʻlmasa
- talaba uchun **maʼlumotnomalarni toʻsish** amalda boʻlsa (cheklov, [20-bob](20-registration.md)); avval uni olib tashlang. Xodim cheklovni koʻra olmasa ham u toʻsadi.
- talaba yozuvi koʻrish qamrovidan tashqarida boʻlsa yoki xodim maʼlumotnoma bera olmasa
- PDF xizmati (Gotenberg) javob bermasa: hech narsa berilmaydi va "PDF yaratib boʻlmadi" koʻrsatiladi. Keyinroq qayta bering.

Berish faoliyat jurnalida qayd etiladi (`certificate.issued`: talaba raqami, tur, til, seriya raqami, nusxalar; maqsad sabab sifatida).

## Berilgan maʼlumotnomalar

**Maʼlumotnomalar > Berilgan maʼlumotnomalar**: berilgan sana, seriya raqami, tur va til, talaba raqami, ism, maqsad, nusxalar, holat, xodim hamda **PDF** va **Tekshirish sahifasi** havolalari (yangi yorliqda). Tur va holat boʻyicha filtrlang; seriya raqami, talaba raqami yoki ism boʻyicha qidiring. Koʻrish qamrovi talaba yozuvlariniki bilan bir xil.

- **PDF**: saqlangan faylni ochadi. U qayta yaratilmaydi, shuning uchun aynan berilgan holatda boʻladi.
- **Tekshirish sahifasi**: ommaviy sahifani ochadi.
- **Qayta yaratish** (qator menyusi): joriy maʼlumotlardan yangi PDF yaratadi, masalan shablon tuzatilgandan keyin, va faylni almashtiradi. Seriya raqami va tekshirish kodi oʻzgarmaydi; nazorat summasi oʻzgaradi. Audit hodisasi `certificate.rerendered`. `certificate_render` buyrugʻi bilan bir xil. Bekor qilingan maʼlumotnomalar qayta yaratilmaydi.
- **Bekor qilish** (qator menyusi): sabab majburiy. Qator va fayl saqlanib qoladi, holat bekor qilingan boʻladi va tekshirish sahifasi "bekor qilingan" deb javob beradi. Audit hodisasi `certificate.revoked`. Bekor qilingan maʼlumotnoma tiklanmaydi; yangisi beriladi.

Reyestr qatorlarini ekranda tahrirlab yoki oʻchirib boʻlmaydi (qator nazorat summasi bilan faqat koʻrish uchun tafsilotlarni ochadi).

## Tekshirish

- Tekshirish URL manzili (`{institution address}/verify/{code}/`) va QR kod maʼlumotnomaning pastki qismida chop etiladi. Kod tasodifiy 20 belgili satrdir (bosh harflar va raqamlar); harflar katta-kichikligi ahamiyatsiz. Manzil `APP_URL` muhit oʻzgaruvchisidan olinadi.
- Sahifa tizimga kirmasdan ochiladi va har bir manzil (IP) uchun daqiqasiga 30 ta soʻrov bilan cheklangan (undan ortigʻiga HTTP 429). Qidiruv tizimlaridan uni indekslamaslik soʻraladi (`noindex`). U maʼlumotnoma berilganmi-yoʻqligini, uning turi, seriya raqami, berilgan sanasi hamda niqoblangan ism va talaba raqamini koʻrsatadi. Bekor qilingan, muddati oʻtgan va nomaʼlum kodlarning har biriga turlicha javob beriladi. Sahifadagi kod maydoni ham kodni tekshiradi (`/verify/?code=...`).
- Topshirilgan PDF faylning oʻzini tekshirish uchun reyestr tafsilotlaridagi nazorat summasini (SHA-256) fayl xeshi bilan solishtiring. `uv run manage.py certificate_verify {code}` buyrugʻi ham kodni tekshiradi ([buyruqlar](../operations/commands.md)).
- Boshqa tizimlar xuddi shu tekshiruvni xuddi shu maʼlumotlar bilan JSON koʻrinishida oladi: `GET /api/v1/certificates/verify/<verification code>/` (tizimga kirishsiz, har bir manzil uchun daqiqasiga 30 ta soʻrov, [LMS integratsiyasi qoʻllanmasi](../../../lms-integration-guide.md)).

## Talaba portali

**Maʼlumotnomalar** (talaba va bitiruvchi menyusi): talabaning oʻz yozuvi boʻyicha berilgan maʼlumotnomalar (berilgan sana, tur va til, seriya raqami, holat), PDF fayllari bilan. Bekor qilinganlari holati bilan, lekin PDF havolasisiz roʻyxatda koʻrsatiladi va talaba bekor qilingan maʼlumotnomaning PDF faylini yuklab ola olmaydi (bergan xodim yozuvni tekshirish uchun uni ochishi mumkin). Boshqa talabalarning fayllarini ochib boʻlmaydi (ilova va maʼlumotlar bazasida taʼminlanadi). PDF manzili `/certificates/{issue id}/download/`.

## Koʻp beriladigan savollar

- **Ism notoʻgʻri yozilgan.** Shaxsning (shu tildagi) ism variantini tuzating va **Qayta yaratish**. Agar maʼlumotnoma allaqachon topshirilgan boʻlsa, uni bekor qiling va yangisini bering.
- **Shablonni oʻzgartirdim; allaqachon berilgan maʼlumotnomalar-chi?** Ular oʻzgarmaydi. Kerak boʻlsa, **Qayta yaratish** (koʻpini birdaniga `certificate_render` buyrugʻi bilan).
- **Seriya raqami tashlab ketildi.** Berish paytida xato yuz berganda (masalan, PDF xizmati ishlamay qolsa), raqam sarflanadi va reyestr qatori qolmaydi. Raqamlarning yagonaligi kafolatlanadi, ketma-ketligi emas.
- **QR kod `localhost` ga yoʻnaltiradi.** Production serverda `APP_URL` ni muassasa manziliga oʻrnating, soʻngra tegishli maʼlumotnomalarni **Qayta yaratish**.

## Ushbu oʻrnatmadagi ekranlar

Ekranlar va funksiyalar asl tizimnikidek (Filament, Livewire); ulardan foydalanish biroz farq qiladi.

- **Maʼlumotnoma berish** dialog oyna oʻrniga shakl sahifasini ochadi. Asl tizim berishdan keyin PDF ni yangi yorliqda ochardi; bu yerda talaba yozuvi ekrani qaytadi va xabardagi **PDF** havolasi uni ochadi.
- Reyestrda **PDF** va **Tekshirish sahifasi** qator oxiridagi havolalardir; **Qayta yaratish** (tasdiqlash sahifasi) va **Bekor qilish** (sabab sahifasi) qator menyusida. Qayta yaratish faqat bekor qilinmagan maʼlumotnomalar uchun ishlaydi.
- Shablonlar tur tahrirlash ekranining pastki qismida tahrirlanadi. Bir til uchun ikkita shablon rad etiladi. Faqat `Asosiy maʼlumotlarni koʻrish` ruxsati bilan turlar va shablonlar faqat koʻrish uchun ochiladi.
- Berish paytida PDF xizmati ishlamay qolsa, hech narsa berilmaydi (asl tizimda PDF siz reyestr qatori qolishi mumkin edi).
- Berish ruxsati faqat umumiy qamrovda berilganda hisobga olinadi (asl tizim qamrovli tayinlashni ekranda oʻtkazib yuborardi, keyin esa maʼlumotlar bazasi qatorni xato bilan rad etardi).
- Demoda (`setup_demo`) `certificate-officer@demo.test` reyestrni, `student@demo.test` esa portaldagi **Maʼlumotnomalar** ni koʻrsatadi.

[Administrator qoʻllanmasi mundarijasi](README.md)
