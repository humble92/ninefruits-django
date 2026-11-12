# 2. Foydalanuvchilar va rollar

## Asosiy tushunchalar

| Atama | Maʼnosi |
|---|---|
| Ruxsat | Bitta funksiyadan foydalanish huquqi. Misollar: `Foydalanuvchilarni koʻrish`, `Ikki bosqichli autentifikatsiyani tiklash` |
| Rol | Ruxsatlar toʻplami. Misollar: Registrator, Kafedra yordamchisi |
| Rol tayinlash | Foydalanuvchiga qamrov va muddat bilan rol berish |
| Qamrov | Rol amal qiladigan joy: **Hammasi**, **Tashkiliy birlik** (fakultet, kafedra va h.k.) yoki **Taʼlim dasturi** |
| Shaxs maqomi roli | Abituriyent, Talaba, Bitiruvchi, Oʻqituvchi, Akademik maslahatchi. Oʻquv maʼlumotlari asosida avtomatik beriladi; qoʻlda tayinlab boʻlmaydi |

Vazifalar oʻzgarganda faqat rol tarkibi yoki tayinlashlar oʻzgaradi, dasturning oʻzi oʻzgarmaydi. Har bir oʻzgarish audit jurnaliga yoziladi. Boshqaruv paneli menyusi va har bir ekrandagi tugmalar ruxsatlarga darhol moslashadi. Djangoning oʻrnatilgan "guruhlar" (groups) va "superfoydalanuvchilar" (superusers) ishlatilmaydi.

## Foydalanuvchi hisobini yaratish

1. **Foydalanuvchilar va kirish > Foydalanuvchilar** boʻlimiga oʻting va **Foydalanuvchi qoʻshish** tugmasini bosing.
2. Ism, e-pochta va tilni kiriting, soʻng **Saqlash** tugmasini bosing.
3. Foydalanuvchi parol oʻrnatish uchun e-pochta orqali havola oladi. Administratorlar parolni hech qachon koʻrmaydi.

Hisoblar oʻchirilmaydi. Hisobni toʻxtatish uchun, masalan xodim ishdan ketganda, foydalanuvchini oching, **Faol** belgisini oʻchiring va saqlang. Faol boʻlmagan hisob bilan tizimga kirib boʻlmaydi va u barcha ruxsatlarini yoʻqotadi. Allaqachon ochiq boʻlgan ekranlar navbatdagi soʻrovda tizimdan chiqariladi.

Hisoblarni tahrirlashdagi himoya choralari

- Oʻz hisobingizni faolsizlantira olmaysiz.
- Sizda boʻlmagan ruxsatlarga ega hisobni (yuqoriroq huquqli administratorni) tahrirlay olmaysiz.
- E-pochta oʻzgartirilsa, e-pochta tasdigʻi bekor qilinadi, shu foydalanuvchining barcha kirish seanslari tugatiladi va `E-pochta oʻzgartirildi` xavfsizlik hodisasi qayd etiladi.
- Foydalanuvchi parolini oʻzgartirsa, boshqa qurilmalardagi seanslar va eslab qolingan qurilmalar tugatiladi hamda `Parol oʻzgartirildi` xavfsizlik hodisasi qayd etiladi.

## Rollarni yaratish va tahrirlash

1. **Foydalanuvchilar va kirish > Rollar** boʻlimiga oʻting va **Rol qoʻshish** tugmasini bosing yoki roʻyxatdan rolni oching.
2. **Ichki nom** kichik lotin harflari va pastki chiziqdan iborat boʻladi (masalan, `exam_office`). Yaratilgandan keyin uni oʻzgartirmagan maʼqul.
3. **Koʻrsatiladigan nom**ni har bir til uchun kiriting. Inglizcha nom majburiy. Til maydonini boʻshatsangiz, shu tildagi nom oʻchiriladi.
4. **Ruxsatlar** boʻlimida funksiyalar boʻyicha ruxsatlarni belgilang. Saqlaganda qoʻshilgan va olib tashlangan ruxsatlar audit jurnaliga yoziladi.

| Rol turi | Tahrirlash | Oʻchirish |
|---|---|---|
| Tizim roli (Tizim administratori) | Faqat nomi. Har doim barcha ruxsatlarga ega | Mumkin emas |
| Shaxs maqomi roli | Koʻrsatiladigan nom va ruxsatlar. Ichki nom emas | Mumkin emas |
| Oddiy rol | Hammasi | Faqat faol tayinlashlari boʻlmaganda |

## Rollarni tayinlash

1. **Foydalanuvchilar va kirish > Foydalanuvchilar** boʻlimiga oʻting va foydalanuvchini oching. Pastdagi **Rol tayinlashlar** roʻyxati joriy va oʻtgan tayinlashlarni koʻrsatadi.
2. Sahifa yuqorisidagi **Rol tayinlash** tugmasini bosing va rol, qamrov, boshlanish/tugash (ixtiyoriy) hamda **Sabab**ni kiriting.
   - Agar qamrov tashkiliy birlik yoki taʼlim dasturi boʻlsa, uni **Qamrov obyekti** maydonida tanlang. Tashkiliy birlik tanlansa, uning ostidagi barcha birliklar ham qamrab olinadi.
   - Darhol amal qilishi uchun boshlanishni boʻsh qoldiring; muddatsiz tayinlash uchun tugashni boʻsh qoldiring.
3. Tayinlashlar hech qachon tahrirlanmaydi. Oʻzgartirish uchun mavjud tayinlashda **Tayinlashni tugatish** tugmasini bosing (sabab majburiy) va yangisini yarating. Tarix toʻliq saqlanadi.

Oʻz tayinlashlaringizni tugata olmaysiz (vazifalarni ajratish tamoyili). Boshqa administratordan soʻrang.

Huquqlarni oshirib olishning oldini oluvchi qoidalar

- Oʻzingizga rol tayinlay olmaysiz.
- Sizda boʻlmagan ruxsatlarni oʻz ichiga olgan rolni tayinlay olmaysiz.
- Qamrovni faqat oʻzingizdagi `Rollarni tayinlash va tugatish` ruxsatining qamrovi doirasida tanlash mumkin. Masalan, bu ruxsatga Muhandislik fakulteti qamrovida ega boʻlgan administrator Hammasi qamrovini yoki boshqa fakultet qamrovini tayinlay olmaydi.
- Birinchi administratorni yaratuvchi `security_create_administrator` buyrugʻini server operatori ishga tushiradi, shuning uchun bu qoidalar unga taalluqli emas ([buyruqlar maʼlumotnomasi](../operations/commands.md)). Djangoning `createsuperuser` buyrugʻidan foydalanib boʻlmaydi.
