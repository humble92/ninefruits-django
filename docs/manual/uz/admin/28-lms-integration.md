# 28. LMS integratsiyasi

Menyu: boshqaruv panelidagi **LMS integratsiyasi > LMS platformalari**, **Kurs bogʻlanishlari**, **Sinxronlash jurnallari** (`LMS platformalari, bogʻlanishlar va sinxronlashni boshqarish` ruxsati; standart: Tizim administratori, Oʻquv-uslubiy boshqarma). Oʻqituvchilar portaldagi **Mening darslarim** va fan guruhi tafsilotlaridagi LMS havolalaridan hamda baho kiritish ekranidagi **Ballarni LMS dan yuklash** dan foydalanadi. Yuklash baho kiritish bilan bir xil shartlarga boʻysunadi (tayinlangan oʻqituvchi, baho kiritish muddati ichida).

Dasturchilar uchun tafsilotlar (konnektor yozish, API) [LMS integratsiyasi qoʻllanmasi](../../../lms-integration-guide.md) da.

## Nima qayerga uzatiladi

| SIS → LMS | Qachon |
|---|---|
| Fan guruhi (kurs yaratish) + oʻqituvchilar | Fan guruhi **eʼlon qilinganda** va `lms_sync` bilan |
| Tasdiqlangan fanga yozilish → kursga yozish | Fanga yozilish, kutish roʻyxatidan oʻtkazish yoki xodim tomonidan fanga yozishda darhol |
| Fandan chiqish yoki voz kechish → kursdan chiqarish | Darhol |
| Toʻliq solishtirish | Har kuni soat 02:30 da (`lms_reconcile`, rejalashtirilgan vazifa `lms.reconcile`) |

| LMS → SIS | Qachon |
|---|---|
| Yakuniy ballar (qoralama) | Oʻqituvchi baho kiritish ekranida **Ballarni LMS dan yuklash** tugmasini bosganda. Saqlash va topshirishni oʻqituvchi bajaradi |

Yakunlangan baholar LMS ga yuborilmaydi. Kurs materiallari, topshiriqlar va testlar LMS da joylashadi.

## Platformalar

**LMS platformalari**: kod, nomi (har bir til uchun), drayver, asosiy URL, kirish maʼlumotlari, faol, talabalar roʻyxatini sinxronlash, yakuniy ballarni olish.

- **Yoʻq (faqat qayd etadi)** drayveri: hech narsani chaqirmaydi va nima yuborilishi kerakligini qayd etadi. Integratsiyadan oldin jarayonni tekshirish yoki namoyish uchun foydalaning. Demo maʼlumotlardagi `DEMO` platformasi undan foydalanadi.
- `Moodle`, `Open edX`: hali konnektor yoʻq ("hali amalga oshirilmagan" deb belgilangan). Ular tanlansa, sinxronlashlar muvaffaqiyatsiz deb qayd etiladi.
- **Faol** yoqilsa, shundan boshlab fan guruhlarini eʼlon qilish va fanlarga yozilishdagi oʻzgarishlar darhol uzatiladi va platforma tungi solishtirishga kiritiladi.
- **Kirish maʼlumotlari** har bir qatorda bitta `key=value` koʻrinishida yoziladi (masalan, `token=...`). Ular shifrlangan holda saqlanadi va hech qachon qayta koʻrsatilmaydi. Tahrirlashda maydonni boʻsh qoldirsangiz, saqlangan qiymatlar saqlanib qoladi. Maʼlumot oʻzgarishlari tarixida ham qiymatlar saqlanmaydi.

## Kurs bogʻlanishlari va sinxronlash jurnallari

- **Kurs bogʻlanishlari**: qaysi fan guruhi qaysi platforma kursiga bogʻlangani (ID, URL), holat (Kutilmoqda/Bogʻlangan/Muvaffaqiyatsiz), oxirgi sinxronlash va xato. Platforma, holat va semestr boʻyicha filtrlar; fan kodi boʻyicha qidiruv. Qator amali **Qayta sinxronlash** (tasdiqlash sahifasi bilan) fan guruhi, oʻqituvchilar va talabalar roʻyxatini qaytadan yuboradi.
- **Sinxronlash jurnallari**: har bir qadam (kurs, aʼzo qoʻshish va olib tashlash, ballarni olish, yetkazilgan ballar, solishtirish) boʻyicha natija va xabar. Muvaffaqiyatsizlik sababini shu yerdan qidiring. Qatorni ochsangiz, boshlanish va tugash vaqtlari hamda maʼlumotlar (payload) koʻrsatiladi.
- Buyruqlar: `uv run manage.py lms_sync {platform} --term={term}` (toʻliq yuborish, `--dry-run`), `uv run manage.py lms_reconcile` (solishtirish). [Operatsion buyruqlar](../operations/commands.md#lms-integratsiyasi-12-bosqich) ga qarang.

## Portal

- Platforma kursi havolasi talabalar va oʻqituvchilar uchun fan tafsilotlarida hamda oʻqituvchining **Mening darslarim** roʻyxatida (**LMS** ustuni; faqat bogʻlangan fan guruhlari) koʻrsatiladi.
- Baho kiritish: platformada **Yakuniy ballarni olish** yoqilgan va fan guruhi bogʻlangan boʻlsa, **Ballarni LMS dan yuklash** tugmasi paydo boʻladi. U faqat ball ustunini toʻldiradi va saqlamaydi.

## Integratsiya API si

API (`/api/v1/lms/platforms/...`) natijalarni keyinroq xabar qiladigan yoki ballarini oʻzi yuboradigan platformalarga xizmat qiladi. Faqat `LMS platformalari, bogʻlanishlar va sinxronlashni boshqarish` ruxsatiga ega alohida integratsiya hisobini yarating; operator uning tokenini `uv run manage.py api_issue_token {email} --days=365` bilan beradi va platforma administratoriga topshiradi. Token faqat bir marta, berilganda koʻrsatiladi. `api_revoke_tokens` uni bekor qiladi. Berish va bekor qilish audit jurnalida qayd etiladi.

- Ballarni yetkazish (`.../scores/`) orqali olingan ballar ham saqlanmaydi. Oʻqituvchi **Ballarni LMS dan yuklash** ni bosganda, olingan oxirgi ballar shaklni qoralama sifatida toʻldiradi.
- Sinxronlash natijalari (`.../sync-results/`) **Sinxronlash jurnallari** da saqlanadi, kurs natijalari esa **Kurs bogʻlanishlari** dagi holatni oʻzgartiradi.

## Koʻp beriladigan savollar

- **LMS da talaba yoʻq.** Talaba sinxronlanishi uchun uning hisobi (foydalanuvchisi) boʻlishi kerak. Hisobi boʻlmasa, uni taklif qiling ([14-bob](14-merge-and-invitations.md)); keyingi solishtirish uni qoʻshadi.
- **Sinxronlash muvaffaqiyatsizligicha qolmoqda.** Sinxronlash jurnalidagi xabarni oʻqing. Koʻpincha kirish maʼlumotlarining muddati oʻtgan boʻladi. Platformaning tahrirlash ekranida qiymatlarni oʻzgartiring va **Qayta sinxronlash**.
- **Platformani almashtirdik.** Yangi platformani yarating va eskisining Faol sozlamasini oʻchiring. Bogʻlanishlar har bir platforma uchun alohida yaratiladi.

## Ushbu oʻrnatmadagi ekranlar

Ekranlar va funksiyalar asl tizimnikidek (Filament, Livewire); baʼzi oʻzaro amallar farq qiladi.

- Kirish maʼlumotlari asl tizimdagi kalit/qiymat jadvali oʻrniga matn maydoniga `key=value` qatorlari sifatida kiritiladi. Notoʻgʻri qatorlar qator raqami bilan rad etiladi.
- Platformaning **parametrlari** (platforma boʻyicha rol ID lari va shu kabilar) uchun ekranda maydon yoʻq. Konnektorga kerak boʻlganda ularni dasturchilar belgilaydi ([integratsiya qoʻllanmasi](../../../lms-integration-guide.md), 3-boʻlim).
- **Qayta sinxronlash** tasdiqlash sahifasi orqali bajariladi. Konnektor xatolari (konnektorsiz drayver, platformadagi uzilish) "Sinxronlash bajarilmadi: ..." xabari sifatida koʻrsatiladi va kurs bogʻlanishi Muvaffaqiyatsiz holatiga oʻtadi (asl tizim xato sahifasini koʻrsatardi).
- Sinxronlash jurnallari faqat koʻrish uchun. Qatorni ochsangiz, maʼlumotlar (payload) JSON koʻrinishida koʻrsatiladi.
- Baho kiritish ekranidagi **Ballarni LMS dan yuklash** jadval ostidagi tugmalar qatorida. U allaqachon yozilganlarni saqlagan holda faqat ball maydonlari oʻzgartirilgan sahifani qayta koʻrsatadi. **Qoralamani saqlash** bosilmaguncha hech narsa saqlanmaydi.
- Integratsiya API si va token buyruqlari (`api_issue_token`, `api_revoke_tokens`) ushbu oʻrnatmada yangi (asl tizimda API yoʻq edi).

[Administrator qoʻllanmasi mundarijasi](README.md)
