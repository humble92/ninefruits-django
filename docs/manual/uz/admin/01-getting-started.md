# 1. Ishni boshlash

## Tizimga kirish

1. Brauzerda `/accounts/login/` manzilini oching. Tizimga kirmagan holda `/portal/` yoki `/admin/` ochilsa ham shu yerga olib keladi, kirgandan keyin esa soʻragan sahifangizga qaytasiz.
2. E-pochta va parolingizni kiriting va **Kirish** tugmasini bosing.
3. Agar ikki bosqichli autentifikatsiyani yoqqan boʻlsangiz, autentifikator ilovasidagi 6 xonali kodni yoki e-pochta orqali olgan kodni kiriting.
4. Shaxsiy kompyuterda **Bu qurilmani eslab qolish** belgisini tanlashingiz mumkin. Belgilangan muddat davomida (standart boʻyicha 30 kun) kod soʻralmaydi. Umumiy foydalaniladigan kompyuterda uni tanlamang.

Parolni unutgan boʻlsangiz, kirish ekranidagi **Parolni unutdingizmi?** orqali tiklash havolasini oling. Bir necha marta muvaffaqiyatsiz kirishga urinishdan keyin tizimga kirish vaqtincha bloklanadi.

Boshqaruv panelining oʻz kirish ekrani yoʻq. `/admin/login/` ham umumiy kirish sahifasiga (`/accounts/login/`) yoʻnaltiradi.

## Portal va boshqaruv paneli

| Ekran | Manzil | Foydalanuvchilar |
|---|---|---|
| Portal | `/portal/` | Barcha foydalanuvchilar. Bosh sahifa (sizning kirish huquqlaringiz), xavfsizlik sozlamalari va foydalanuvchi rollariga (talaba, oʻqituvchi, maslahatchi, abituriyent) mos menyular |
| Boshqaruv paneli | `/admin/` | `Boshqaruv panelini ochish` ruxsatiga ega xodimlar |

Ikkala ekran uchun bitta kirish ishlatiladi.

- Portalning yuqorisidagi menyu faqat foydalanuvchi rollari (talaba, oʻqituvchi, ...) va ruxsatlariga mos bandlarni koʻrsatadi. `Boshqaruv panelini ochish` ruxsati boʻlsa, **Boshqaruv** bandi boshqaruv paneliga olib boradi.
- Boshqaruv panelining yuqori oʻng burchagidagi foydalanuvchi menyusida **Ikki bosqichli autentifikatsiya** (portal xavfsizlik sozlamalari) va **Portal** havolalari hamda tizimdan chiqish (**Chiqish**) bor. Birinchi sahifa (**Boshqaruv paneli**) hisob nomi va e-pochtasini, portal havolasini va chiqish tugmasini koʻrsatadi.
- Ruxsati boʻlmagan hisob bilan boshqaruv paneli manzili ochilsa, "403 Forbidden" koʻrsatiladi.

Boshqaruv panelining chap tomonidagi menyu ruxsatlaringizga bogʻliq. U asl guruhlar tartibini saqlaydi (Talabalar va xodimlar, Qabul, Oʻquv reja va fan guruhlari, Fanlarga yozilish, Baholar, Fan soʻrovnomasi, Imtihonlar, Maʼlumotnomalar, Bitiruv, Hisobotlar, LMS integratsiyasi, Asosiy maʼlumotlar, Foydalanuvchilar va kirish, Audit, Sozlamalar); siz ochishingiz mumkin boʻlgan birorta ekrani boʻlmagan guruhlar koʻrsatilmaydi. Agar biror menyu koʻrinmasa, tizim administratoridan rol tayinlashni soʻrang. Menyu ustidagi qidiruv maydoni menyu bandlarini nomi boʻyicha topadi.

## Ikki bosqichli autentifikatsiya haqida eslatma

Ikki bosqichli autentifikatsiya siyosati "tavsiya etiladi" boʻlganda yoki majburiy siyosatning imtiyozli muddati davomida portal va boshqaruv panelining yuqorisida eslatma chiqadi. **Hozir sozlash** portalning xavfsizlik sahifasini ochadi. [3. Ikki bosqichli autentifikatsiya](03-two-factor-authentication.md) ga qarang.

## Til

Tilni portal yuqorisidagi til tanlagich (kirish ekranida ham xuddi shunday tanlagich bor) yoki boshqaruv paneli foydalanuvchi menyusidagi tillar roʻyxati orqali oʻzgartiring. Tizimga kirgan holda oʻzgartirsangiz, tanlov hisobingizda saqlanadi va keyingi kirishda ham amal qiladi. Qaysi tillar taklif qilinishini tizim administratori **Sozlamalar > Muassasa** boʻlimida belgilaydi.
