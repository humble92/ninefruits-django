# 15. Kirish usullari

Menyu: **Sozlamalar > Kirish usullari** (`Kirish usullari va SSO ni boshqarish` ruxsati)

## Kirish nomi

Hisobning e-pochtasi standart kirish nomi hisoblanadi. Talaba raqami orqali kirish yoqilganda kirish ekranidagi maydon "E-pochta yoki talaba raqami" boʻladi.

| Talaba raqami bilan kirish | Ishlash tartibi |
|---|---|
| Ruxsat etilmagan | Faqat e-pochta |
| Faqat amaldagi talabalar | Oʻqiyotgan va akademik taʼtildagi yozuvlarning talaba raqamlari bilan kirish mumkin |
| Amaldagi talabalar va bitiruvchilar | Yakunlangan yozuvlarning (bitirgan, oʻqishdan chiqqan va h.k.) talaba raqamlari bilan ham kirish mumkin |

Bir nechta talaba yozuviga ega shaxs qaysi talaba raqamidan foydalanmasin, bitta hisobga kiradi.

## Hisobni bloklash

| Sozlama | Tavsif |
|---|---|
| Muvaffaqiyatsiz urinishlardan keyin bloklash | Ketma-ket shuncha marta notoʻgʻri parol kiritilganda hisob bloklanadi. 0 bloklashni oʻchiradi |
| Bloklash muddati (daqiqa) | Shu vaqtdan keyin blok avtomatik ravishda olib tashlanadi |

E-pochta va talaba raqami orqali qilingan urinishlar bitta hisobning muvaffaqiyatsiz urinishlari sifatida hisoblanadi. Bloklangan hisobga notoʻgʻri parol bilan bir xil xabar koʻrsatiladi, shuning uchun hisob mavjudligi oshkor boʻlmaydi. Bloklashlar xavfsizlik hodisasi sifatida qayd etiladi (**Kirish bloklandi**).

Blokni muddatidan oldin olib tashlash uchun **Foydalanuvchilar** batafsil sahifasidagi **Kirishni blokdan chiqarish** amalidan foydalaning (sabab majburiy, `Foydalanuvchilarni tahrirlash` ruxsati). Boshqaruv paneli ishlamayotganda IT operatori `uv run manage.py security_unlock_user` buyrugʻidan foydalanadi.

## Universitet hisobi orqali kirish (SSO)

Universitetning OpenID Connect orqali kirish tizimi (masalan, Microsoft Entra ID, Google Workspace, Keycloak) roʻyxatdan oʻtkazilganda kirish ekraniga "... orqali kirish" tugmasi qoʻshiladi.

| Maydon | Tavsif |
|---|---|
| Kalit | Kichik harflardagi identifikator, masalan `school`. Uni oʻzgartirish mavjud bogʻlanishlarni buzadi |
| Tugma yozuvi | Kirish ekranida koʻrsatiladigan nom |
| Issuer URL | Provayderning issuer manzili. Bu manzil ostida `/.well-known/openid-configuration` mavjud boʻlishi kerak |
| Client ID, Client secret | Ilovani provayderda roʻyxatdan oʻtkazishda olingan qiymatlar. Secret shifrlangan holda saqlanadi |
| Scopes | Standart qiymat `openid email profile` |
| Ikki bosqichli autentifikatsiya sifatida hisoblanadi | Faqat universitet hisobi orqali kirishning oʻzi ikki bosqichli autentifikatsiyani talab qilganda yoqing. Yoqilganda bu kirish usulida bu yerda ikki bosqichli autentifikatsiya qayta soʻralmaydi |
| Provayderda roʻyxatdan oʻtkaziladigan Redirect URI | Ekranda koʻrsatilgan manzilni (`https://<server>/auth/sso/<key>/callback/`) provayderning ilova sozlamalarida aynan shu koʻrinishda roʻyxatdan oʻtkazing |

### Hisoblarni bogʻlash

| Rejim | Ishlash tartibi |
|---|---|
| Foydalanuvchilar hisoblarini oʻzlari bogʻlaydi | Foydalanuvchi parol bilan kiradi va portaldagi **Xavfsizlik > Universitet hisobi orqali kirish** boʻlimida **Bogʻlash** tugmasini bosadi (parolni tasdiqlash talab qilinadi) |
| Tasdiqlangan universitet e-pochtasi orqali avtomatik bogʻlash | Provayder tasdiqlagan e-pochta talaba yozuvidagi universitet e-pochtasiga mos kelsa, hisob birinchi kirishda avtomatik bogʻlanadi |

- Bogʻlanmagan universitet hisobi bilan kirilganda parol bilan kirib, hisobni bogʻlash haqida xabar koʻrsatiladi. Universitet hisobining oʻzi hech qachon yangi hisob yaratmaydi.
- Bogʻlash va bogʻlanishni bekor qilish xavfsizlik jurnalida qayd etiladi.

### Parol bilan kirishga ruxsat berish

**Universitet hisobi orqali kiradiganlarga parolga ruxsat berish** oʻchirilsa, bogʻlangan foydalanuvchilar faqat universitet hisobi orqali kira oladi. Universitet hisoblari koʻpincha bitiruvdan keyin oʻchirilgani sababli, bu sozlamani yoqilgan holda qoldirish va bitirish arafasidagi talabalardan shaxsiy e-pochta va parol tayyorlashni soʻrash tavsiya etiladi. Bitiruvchilar hisobning kirish e-pochtasi (shaxsiy e-pochta) va paroli bilan kirishda davom etadi.
