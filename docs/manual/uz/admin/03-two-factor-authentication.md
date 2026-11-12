# 3. Ikki bosqichli autentifikatsiya

## Foydalanuvchilar uni qanday yoqadi

Foydalanuvchilar ikki bosqichli autentifikatsiyani portalning **Xavfsizlik** sahifasida yoqadi (`/portal/security/`, boshqaruv panelida foydalanuvchi menyusidagi **Ikki bosqichli autentifikatsiya**). Yoqish yoki oʻchirishdan oldin parol yana bir marta tasdiqlanadi.

### Autentifikator ilovasi (tavsiya etiladi)

1. **Ikki bosqichli autentifikatsiyani yoqish** tugmasini bosing.
2. QR kodni Google Authenticator yoki Microsoft Authenticator kabi autentifikator ilovasi bilan skanerlang.
3. Ilovada koʻrsatilgan 6 xonali kodni kiriting va **Tasdiqlash** tugmasini bosing.
4. Ekranda koʻrsatilgan **tiklash kodlari**ni xavfsiz joyda saqlang. Telefon yoʻqolsa, ularning har biridan bir marta foydalanish mumkin.

### E-pochta kodi

Faqat tizim administratori ruxsat bergan taqdirdagina koʻrsatiladi. U autentifikator ilovasidan foydalana olmaydigan foydalanuvchilar uchun moʻljallangan va ilovaga qaraganda kamroq xavfsiz.

1. **E-pochta kodi** boʻlimida **Sozlash uchun kod yuborish** tugmasini bosing.
2. Hisob e-pochtasiga yuborilgan 6 xonali kodni kiriting va **Tasdiqlash** tugmasini bosing.
3. Shundan keyin har safar tizimga kirganda e-pochtaga kod keladi. Kod 10 daqiqa ichida bir marta ishlatilishi mumkin; 5 marta notoʻgʻri kiritilgandan keyin yangi kod kerak boʻladi. Kod daqiqasiga bir marta va soatiga koʻpi bilan 5 marta yuborilishi mumkin.

Ikkala usulni ham yoqish mumkin. Siyosat "majburiy" boʻlsa, oxirgi qolgan usulni oʻchirib boʻlmaydi.

## Siyosat sozlamalari (tizim administratori)

Boshqaruv panelidagi **Sozlamalar > Xavfsizlik** boʻlimida sozlanadi. Saqlangandan keyin barcha foydalanuvchilarga ularning navbatdagi sahifa yuklanishidan boshlab qoʻllanadi.

| Sozlama | Tavsifi |
|---|---|
| Siyosat | **Ishlatilmaydi** / **Tavsiya etiladi (ixtiyoriy)**: yoqmagan foydalanuvchilar faqat eslatmani koʻradi / **Tanlangan rollar uchun majburiy**: tanlangan rollarga ega foydalanuvchilar yoqishi shart / **Hamma uchun majburiy** |
| Ikki bosqichli autentifikatsiya majburiy boʻlgan rollar | Siyosat "Tanlangan rollar uchun majburiy" boʻlganda tanlanadi |
| Imtiyozli muddat (kun) | Talab foydalanuvchiga birinchi marta qoʻllangandan keyin u yoqmasdan ishlashni davom ettira oladigan muddat. Bu muddat davomida portal va boshqaruv panelining yuqorisida muddat haqida eslatma chiqadi. Muddat oʻtgach, faqat xavfsizlik sahifasidan foydalanish mumkin. 0 darhol degani |
| Qurilmalarni eslab qolish (kun) | **Bu qurilmani eslab qolish** tanlangan qurilmada kod soʻralmaydigan muddat. 0 bu funksiyani oʻchiradi |
| E-pochta kodlariga ruxsat berish | Oʻchirilganda e-pochta kodlari ikki bosqichli autentifikatsiya hisoblanmaydi. Faqat e-pochta kodini yoqqan foydalanuvchilardan siyosatga muvofiq autentifikator ilovasini yoqish soʻraladi |

Tavsiya etilgan amaliyot: xodimlar rollari (Registrator, Oʻquv-uslubiy boshqarma, Tizim administratori va h.k.) uchun **Tanlangan rollar uchun majburiy**, talabalar uchun tavsiya etiladi.

## Tiklash (telefon yoʻqolganda va h.k.)

1. Foydalanuvchini **Foydalanuvchilar va kirish > Foydalanuvchilar** boʻlimida oching.
2. Sahifa yuqorisidagi **Ikki bosqichli autentifikatsiyani tiklash** tugmasini bosing va sababni kiriting (`Ikki bosqichli autentifikatsiyani tiklash` ruxsati kerak).
3. Foydalanuvchining autentifikator ilovasi, tiklash kodlari, e-pochta kodi va eslab qolingan qurilmalari toʻliq tozalanadi. Imtiyozli muddat qaytadan boshlanadi.

Oʻz hisobingizni tiklay olmaysiz. Tiklash sababi bilan birga xavfsizlik hodisasi sifatida va faoliyat jurnalida qayd etiladi.

Agar yagona administrator telefonini yoʻqotib, boshqaruv paneliga kira olmasa, IT operatori uni `uv run manage.py security_reset_mfa` buyrugʻi bilan tiklaydi (Docker: `docker compose exec app uv run manage.py security_reset_mfa`, [buyruqlar maʼlumotnomasi](../operations/commands.md)).
