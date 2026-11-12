# 12. Shaxslar va talaba yozuvlari

Menyu: **Talabalar va xodimlar > Shaxslar**, **Talaba yozuvlari**, **Oʻqituvchilar**

## Shaxslar va talaba yozuvlari qanday bogʻlangan

| Tushuncha | Tavsifi |
|---|---|
| Shaxs | Bitta inson. Ism, tugʻilgan sana, aloqa maʼlumotlari, shaxsni tasdiqlovchi raqamlar, surat, vasiylar. Talaba boʻladimi yoki oʻqituvchi, bitta inson — bitta shaxs |
| Talaba yozuvi | Bitta qabul. Talaba raqami, taʼlim dasturi, qabul sanasi, kurs, maqom. Bitirib, keyin qayta qabul qilingan talaba oʻsha shaxsning oʻzida **yangi talaba yozuvi (yangi talaba raqami)** oladi |
| Oʻqituvchi | Shaxsning oʻqituvchi maʼlumotlari (xodim raqami, tashkiliy birlik, ish turi, ilmiy unvon). Har bir shaxs uchun bitta |
| Hisob | Tizimga kirish hisobi. Shaxs bilan 1:1 bogʻlangan. Bir nechta talaba yozuviga ega shaxsda ham bitta hisob boʻladi |

Talabalar va bitiruvchilar portalda talaba yozuvini tanlaydi (bir nechta boʻlsa, yuqorida yozuv tanlagich chiqadi).

## Shaxslar

- Shaxsda ham **Lotin yozuvidagi ism** (pasportdagi rasmiy ism: familiya, ism), ham **Boshqa tillardagi ism** (masalan, koreyscha `김민수`) boʻladi. Ekranlarda joriy tildagi ism boʻlsa, u koʻrsatiladi, aks holda lotin yozuvidagi ism. Qidiruv ikkalasini ham topadi.
- JShShIR va pasport raqamlari shifrlangan holda saqlanadi va yashirilgan holda koʻrsatiladi. Shaxs sahifasi yuqorisidagi **JShShIR ni koʻrsatish** (yoki **Pasport raqamini koʻrsatish**) tugmasini bosib, sababni kiritgandan keyin toʻliq qiymat alohida sahifada bir marta koʻrsatiladi (`JShShIR va pasport raqamlarini ochib koʻrish` ruxsati). Qiymat hech qayerda saqlanmaydi (xabarda ham, jurnalda ham), ochib koʻrish esa sababi bilan xavfsizlik jurnaliga yoziladi. Raqam boʻyicha qidiruv faqat aniq mosliklarni topadi.
- Suratlar shaxsning tahrirlash sahifasida yuklanadi. Suratni faqat ruxsat tekshiruvidan keyin yuklab olish mumkin (ochiq manzili yoʻq).
- Vasiylar shaxsning batafsil sahifasidagi **Vasiylar** yorligʻida boshqariladi. Talabalar ham portaldagi **Mening maʼlumotlarim** boʻlimida oʻz vasiylari va aloqa maʼlumotlarini (e-pochta, telefon, manzil, pochta indeksi) tahrirlashi mumkin. Ular ismini, tugʻilgan sanasini yoki shaxsni tasdiqlovchi raqamlarini oʻzgartira olmaydi.
- Shaxs sahifasi pastidagi **Oʻzgarishlar tarixi** shaxs va uning vasiylari maʼlumotlaridagi oxirgi 50 ta oʻzgarishni (vaqt, jadval, oʻzgargan ustunlar, foydalanuvchi) koʻrsatadi. `Audit yozuvlarini koʻrish` ruxsati bilan har bir oʻzgarishni (oldingi va keyingi qiymatlar) ochish mumkin. Talaba yozuvi sahifasi ham yozuv tarixini, uning maqom oʻzgarishlari, akademik maslahatchilari, ikkinchi mutaxassisliklari va qoʻshimcha yoʻnalishlarini xuddi shunday koʻrsatadi.

| Ruxsat | Nimaga imkon beradi |
|---|---|
| `Barcha shaxslarni koʻrish` | Barcha shaxslarni koʻrish |
| `Shaxslarni yaratish va tahrirlash` | Shaxslarni yaratish va tahrirlash |
| `JShShIR va pasport raqamlarini ochib koʻrish` | JShShIR va pasport raqamlarini toʻliq koʻrish |
| `Takroriy shaxslarni birlashtirish`, `Shaxslarni hisob yaratishga taklif qilish` | [14-bob](14-merge-and-invitations.md) |

`Barcha shaxslarni koʻrish` ruxsati boʻlmagan xodimlar ham oʻzlari koʻrishi mumkin boʻlgan talaba yozuvlari ortidagi shaxslar va oʻqituvchilarni koʻra oladi.

## Talabani roʻyxatga olish

1. **Talaba yozuvlari** roʻyxati yuqorisidagi **Talaba yozuvi qoʻshish** tugmasini bosing (sahifa sarlavhasi **Talabani roʻyxatga olish**).
2. **Mavjud shaxs**ni tanlang (oʻqishga qayta tiklash, magistraturaga kirayotgan oʻqituvchi va h.k.) yoki **Yangi shaxs**ni kiriting. Yangi shaxs yaratishdan oldin xuddi shu shaxs allaqachon mavjud emasligini qidiruv orqali tekshiring.
3. Taʼlim dasturi, qabul sanasi, kurs va qabul turini kiriting. Boshqaruvchi tashkiliy birlik taʼlim dasturidan olinadi.
4. Talaba raqamini **Sozlamalar > Talaba yozuvlari** dagi talaba raqami shabloni boʻyicha yaratish uchun uni boʻsh qoldiring. Standart shablon `{YYYY}{SEQ:5}` — qabul yili va 5 xonali tartib raqami (masalan, `202600001`). Allaqachon ishlatilgan raqamlar (import qilingan yozuvlarnikini ham) tashlab oʻtiladi.

| Talaba raqami belgisi | Maʼnosi |
|---|---|
| `{YYYY}` | Qabul yili |
| `{YY}` | Qabul yilining oxirgi ikki raqami |
| `{SEQ:n}` | n xonagacha nollar bilan toʻldirilgan tartib raqami. Shablonda aynan bitta boʻlishi shart. Har bir prefiks (masalan, `2026`) uchun alohida hisoblanadi |

Yozuvning talaba raqami va maqomi tahrirlash sahifasida oʻzgartirilmaydi. Maqom maqom oʻzgarishlari orqali oʻzgaradi ([13-bob](13-status-changes-and-advisors.md)).

## Talaba yozuvlarini koʻrish qamrovi

| Ruxsat qamrovi | Koʻrish mumkin boʻlgan talaba yozuvlari |
|---|---|
| `Talaba yozuvlarini koʻrish` yoki `Talaba yozuvlarini yaratish va tahrirlash`, Hammasi qamrovi | Barcha talaba yozuvlari |
| Tashkiliy birlik qamrovi | Shu birlik va uning quyi birliklaridagi yozuvlar (masalan, Muhandislik fakulteti qamrovi = fakultetning barcha kafedralari) |
| Taʼlim dasturi qamrovi | Shu taʼlim dasturidagi yozuvlar |
| Tashkiliy birlik yoki taʼlim dasturi qamrovi (ikkinchi mutaxassisliklar va qoʻshimcha yoʻnalishlar) | Shu birlik yoki dasturni ikkinchi mutaxassislik yoki qoʻshimcha yoʻnalish sifatida oʻqiyotgan talabalar yozuvlari (faqat koʻrish) |
| Ikkinchi mutaxassislik va qoʻshimcha yoʻnalishni tasdiqlovchi | Qaror qabul qilinishi kerak boʻlgan ariza topshirgan talabalar yozuvlari (faqat koʻrish) |
| Akademik maslahatchi | Joriy maslahat oluvchilar |
| Talabaning oʻzi | Oʻz yozuvlari |

Xuddi shu qoidalar maʼlumotlar bazasida ham mavjud (qator darajasidagi xavfsizlik), shuning uchun ekranlardan tashqaridagi soʻrovlar (hisobotlar, bevosita ulanishlar) ham qamrovdan chiqa olmaydi.

## Oʻqituvchilar

**Oʻqituvchilar** roʻyxati yuqorisidagi **Oʻqituvchi qoʻshish** tugmasi bilan (sahifa sarlavhasi **Yangi oʻqituvchi**) mavjud shaxsni tanlang yoki yangisini kiriting (`Oʻqituvchilarni boshqarish` ruxsati). Tugash sanasi oʻtgach, oʻqituvchi joriy oʻqituvchilar roʻyxatidan (standart filtr) va akademik maslahatchi tanlagichidan chiqib ketadi.

## CSV orqali koʻp yozuvlarni birdaniga yuklash

Talaba yozuvlari va oʻqituvchilar roʻyxatlari yuqorisidagi **CSV import qilish** tugmasidan foydalaning. Ustun formatlari [9-bob](09-csv-import.md#talabalar-va-oʻqituvchilar)da keltirilgan.
