# 26. Bitiruv talablarini tekshirish va bitiruv

Menyu: **Bitiruv > Bitiruv talablari tekshiruvlari**, talaba yozuvini koʻrish ekranidagi **Bitiruv talablarini tekshirish** tugmasi, **Sozlamalar > Bitiruv sozlamalari** (diplom raqami shabloni, minimal umumiy GPA; `Bitiruvni rasmiylashtirish, talablardan ozod qilish` ruxsati). Talabalar oʻz holatini portaldagi **Bitiruv talablari** boʻlimida koʻradi.

| Ruxsat | Nimaga imkon beradi |
|---|---|
| `Bitiruv talablari tekshiruvlarini bajarish va koʻrish` | Tekshiruvlarni bajarish (yakka va ommaviy) va saqlangan tekshiruvlarni koʻrish |
| `Bitiruvni rasmiylashtirish, talablardan ozod qilish` | Bitiruvni rasmiylashtirish (ommaviy), talablardan ozod qilish |

Rollar boʻyicha standart sozlamalar: Registratorda ikkalasi ham, Oʻquv-uslubiy boshqarmada tekshiruvlar ruxsati bor.

## Eski tizimdan farqlari

- **Talablar tekshiriladi.** Eski tizimning (YUSTIC) bitiruvni tekshirish varaqasi faqat fan toifalari boʻyicha kreditlar va GPA ni chop etardi va ularni hech narsa bilan solishtirmasdi (tekshiruv natijasi katagi boʻsh edi). Yangi tizim har bir oʻquv reja yili uchun **bitiruv talablari** bilan solishtiradi ([17-bob](17-courses-and-curriculum.md)) va har bir talab bajarilganmi-yoʻqligini koʻrsatadi.
- **Bitiruvdan oldin tekshiruv majburiy.** Eski tizimda Z maqom oʻzgarishi kodini kiritishning oʻzi yetarli edi. Yangi tizim bitiruvni faqat oxirgi saqlangan tekshiruv bajarilgan boʻlsagina rasmiylashtiradi.
- **Diplom raqamini tizim beradi.** Eski tizim diplom raqami maydonidan foydalanmasdi va diplom raqami qoʻlda yozilardi.
- Bitiruvchilar boshqa jadvalga koʻchirilmaydi. Faqat talaba holati `Bitirgan` ga oʻzgaradi va hisob bitiruvchi huquqlarini saqlab qoladi ([13-bob](13-status-changes-and-advisors.md)).

## Tekshirish qoidalari

Talabaning **asosiy dasturi × oʻquv reja yili** uchun talablar toʻplami topiladi va har bir talab tekshiriladi.

| Talab turi | Tekshiruv |
|---|---|
| Toifa boʻyicha kreditlar | Toifasi shu toifa **yoki undan quyi toifa** boʻlgan oʻzlashtirilgan fanlar kreditlari yigʻindisi ≥ minimal kreditlar |
| Majburiy fanlar | Roʻyxatdagi barcha fanlar oʻzlashtirilgan. Fanga yozilish paytida amal qilgan **muqobil fanlar** hisobga olinadi |
| Fanlardan tanlash | Roʻyxatdagi (muqobillar bilan birga) oʻzlashtirilgan fanlar kreditlari yoki soni chegaraga teng yoki undan yuqori |
| Topshirilgan imtihon | Shu imtihon turi boʻyicha oʻtgan natija mavjud ([24-bob](24-assessments.md)) |

- "Oʻzlashtirilgan" yakunlangan bahosi oʻtish bahosi boʻlgan (`is_passed`) fanga yozilishni anglatadi. Shu shaxsning boshqa talaba yozuvlarida (oʻqishga qayta tiklanishdan oldin) oʻzlashtirilgan fanlar ham hisobga olinadi.
- Talablar toʻplamining **jami kreditlari** va **Sozlamalar > Bitiruv sozlamalari** dagi **minimal umumiy GPA** (standart 2.0; boʻsh: qoʻllanilmaydi) ham tekshiriladi.
- Ikkinchi mutaxassislik va qoʻshimcha yoʻnalishlar oʻz talablar toʻplamlari boʻyicha alohida tekshiriladi va birga koʻrsatiladi. Bitirish sharti — asosiy dastur talablarining bajarilishi.
- Oʻquv reja yiliga mos talablar toʻplami boʻlmasa, tekshiruv bajarilmagan hisoblanadi (toʻplamni yaratish kerak).

## Tekshiruvlar

- **Hozir tekshirish**: talaba yozuvini koʻrish ekranidagi **Bitiruv talablarini tekshirish** tugmasi. U joriy maʼlumotlarni darhol tekshiradi va har bir talab boʻyicha oʻzlashtirilgan va yetishmayotgan fanlarni koʻrsatadi. **Bu tekshiruvni saqlash** uni saqlaydi.
- **Ommaviy tekshiruvlar**: **Bitiruv talablari tekshiruvlari > Tekshiruvlarni bajarish** (semestr, qaysi kursdan) yoki `uv run manage.py degree_audit_run --term={term} --min-year-level=4 --actor=...` buyrugʻi ([operatsion buyruqlar](../operations/commands.md)). Har bir oʻqiyotgan talaba uchun tekshiruv saqlanadi.
- Saqlangan tekshiruv **holat surati** hisoblanadi. Keyingi baho oʻzgarishlari unga taʼsir qilmaydi; qayta tekshirish yangi surat qoʻshadi. Roʻyxat har bir talaba va dasturdagi oʻrin uchun faqat **oxirgi** tekshiruvni koʻrsatadi, bitiruvni rasmiylashtirish ham oxirgi tekshiruvga qaraydi.

## Talablardan ozod qilish

Mutaxassislikni oʻzgartirish, oʻqishni koʻchirish orqali qabul yoki almashinuv dasturi kabi individual holatlar uchun bitta talabdan ozod qilinadi. Bunda ikki kishi ishtirok etadi (2026-10-23 dagi qaror).

1. **Soʻrov**: talaba yozuvini koʻrish ekranidagi **Talabdan ozod qilish** boʻlimida talabni tanlang va sababni koʻrsating (`Bitiruvni rasmiylashtirish, talablardan ozod qilish` ruxsati). Audit hodisasi `graduation.waiver_requested`.
2. **Tasdiqlash yoki rad etish**: **Bitiruv > Talablardan ozod qilishlar** boʻlimida xuddi shu ruxsatga ega **boshqa xodim** tasdiqlaydi (izoh ixtiyoriy) yoki rad etadi (izoh majburiy). Hech kim oʻz soʻrovi boʻyicha qaror qabul qila olmaydi. Audit hodisalari `graduation.waiver_approved`/`waiver_rejected`.
3. Tekshiruvda faqat tasdiqlangan ozod qilishlar bajarilgan deb hisoblanadi. Har bir talab uchun bitta koʻrib chiqilayotgan yoki tasdiqlangan ozod qilish.
4. **Bekor qilish**: tasdiqlangan ozod qilishda **Ozod qilishni bekor qilish** (sabab majburiy) uning qoʻllanilishini toʻxtatadi va tarixni saqlaydi (holat `Bekor qilingan`, audit hodisasi `graduation.waiver_lifted`). Allaqachon rasmiylashtirilgan talabaning bitiruvi bekor qilinmaydi.

Har bir qadam maʼlumot oʻzgarishi yozuvida ham koʻrinadi.

## Bitiruvni rasmiylashtirish

**Bitiruv talablari tekshiruvlari** roʻyxatida talabalarni tanlang va **Bitirtirish** tugmasini bosing (bitirish sanasi, sabab). Har bir talaba uchun:

1. Talaba oʻqiyotganligi va asosiy dastur boʻyicha oxirgi tekshiruv bajarilganligi tekshiriladi. Aks holda bu talaba oʻtkazib yuboriladi va sababi koʻrsatiladi.
2. `Bitirish` maqom oʻzgarishi qayd etiladi (holat `Bitirgan`, bitirish sanasi). U [13-bob](13-status-changes-and-advisors.md) dagi maqom oʻzgarishlari tarixida koʻrinadi.
3. Diplom raqami beriladi. Shablon **Sozlamalar > Bitiruv sozlamalari** dagi `{PROGRAM}-{YYYY}-{SEQ:5}` (standart, masalan `CS-2026-00001`; tokenlar: `{PROGRAM}` dastur kodi, `{YYYY}`, `{YY}` bitirish yili, `{SEQ:n}` har bir prefiks boʻyicha tartib raqami). Bir vaqtda rasmiylashtirishda raqamlar hech qachon toʻqnashmaydi.
4. Audit hodisasi `graduation.processed` (talaba raqami, bitirish sanasi, diplom raqami, asos qilingan tekshiruv).

Bitiruvchilar portalda oʻz baholari va maʼlumotnomalarini koʻrishda davom etadi, bitirganlik haqida maʼlumotnomada esa bitirish sanasi va diplom raqami chop etiladi ([23-bob](23-certificates.md)). Notoʻgʻri bitiruv maqom oʻzgarishi (oʻqishga qayta tiklash va shu kabilar) orqali tuzatiladi. Bitiruvni bekor qilish funksiyasi yoʻq.

## Koʻp beriladigan savollar

- **Tekshiruv "talablar toʻplami yoʻq" deb koʻrsatyapti.** Dasturda talabaning oʻquv reja yilini qamrab oladigan bitiruv talablari toʻplami yoʻq. Uni [17-bob](17-courses-and-curriculum.md) dagidek yarating.
- **Muqobil fan tan olinmayapti.** Muqobillikning amal qilish muddati fan oʻqilgan semestrning boshlanish sanasini oʻz ichiga olishi kerak.
- **Diplom raqami shablonini oʻzgartirsam nima boʻladi?** U keyingi berishdan boshlab qoʻllaniladi. Prefiks oʻzgarganda tartib raqami yana 1 dan boshlanadi.

## Ushbu oʻrnatmadagi ekranlar

Ekranlar va funksiyalar asl tizimnikidek (Filament, Livewire); baʼzi boshqaruv elementlari biroz boshqacha ishlaydi.

- **Bitiruv > Bitiruv talablari tekshiruvlari** roʻyxati (`/admin/graduation/degreeaudit/`): filtrlar standart holatda dastur roli **Asosiy dastur** va talaba holati **Oʻqimoqda**. Qatordagi **Ochish** saqlangan tekshiruvni koʻrsatadi; **Qayta tekshirish** tasdiqlash sahifasini ochadi. **Tekshiruvlarni bajarish** roʻyxat ustidagi amal tugmasi (semestr, qaysi kursdan, standart 4).
- **Bitirtirish** uchun qatorlarni belgilang, amallar roʻyxatidan **Bitirtirish** ni tanlang va bajaring: sahifa bitirish sanasi va sababni soʻraydi. Qayta ishlab boʻlmagan talabalar talaba raqami va sababi bilan ogohlantirish sifatida koʻrsatiladi (10 tagacha).
- Talaba yozuvidagi **Bitiruv talablarini tekshirish** hozir baholangan tekshiruvni alohida sahifada koʻrsatadi; pastdagi **Bu tekshiruvni saqlash** uni saqlaydi. **Talabdan ozod qilish** talabni tanlash va sababni koʻrsatish sahifasini ochadi.
- **Bitiruv > Talablardan ozod qilishlar** (`/admin/graduation/degreerequirementwaiver/`): holat filtri standart holatda **Kutilmoqda**, menyu esa kutilayotganlar sonini koʻrsatadi. Qatordagi **Tasdiqlash**, **Rad etish** va **Ozod qilishni bekor qilish** izoh (sabab) sahifasini ochadi. Ularni oʻz soʻrovingiz yoki allaqachon qaror qabul qilingan ozod qilish uchun ochish 403 qaytaradi.
- **Sozlamalar > Bitiruv sozlamalari** (`/admin/settings/graduation/`): diplom raqami shabloni faqat aynan bitta `{SEQ:n}` bilan saqlanadi. Minimal umumiy GPA 0 dan 5 gacha; boʻsh boʻlsa, qoʻllanilmaydi.
- Portaldagi **Bitiruv talablari** (`/portal/graduation/`): talabalar va bitiruvchilar menyusida. Bir nechta talaba yozuvi boʻlsa (qayta tiklanish), portalda tanlangan yozuvdan foydalanadi.
- Bitiruv ruxsatlar (bitiruvni qayta ishlash, yozuv qamrovi, maqom oʻzgarishini tasdiqlash qamrovi) tekshirilgandan keyin maqom oʻzgarishi va diplom raqamini tizim kontekstida yozadi, shuning uchun bitiruv xodimlariga `Talaba yozuvlarini yaratish va tahrirlash` ruxsati qoʻshimcha kerak emas. Maʼlumot oʻzgarishlari jurnali baribir uni qayta ishlagan foydalanuvchini koʻrsatadi.

[Administrator qoʻllanmasi mundarijasi](README.md)
