# 6. Kodlar roʻyxati, davlatlar, tillar

Menyu: **Asosiy maʼlumotlar > Kodlar roʻyxatlari**, **Davlatlar**, **Tillar** (`Kodlar roʻyxati, davlatlar va tillarni boshqarish` ruxsati)

## Kodlar roʻyxati

Universitetdan universitetga farq qiladigan qisqa roʻyxatlar. Har bir roʻyxat (tur) oʻz kod qiymatlariga ega.

| Roʻyxat kodi | Vazifasi | Eski tizim (YUSTIC) |
|---|---|---|
| `ethnicity` | Millati | `FNATION` |
| `admission_type` | Qabul turi | `FADMDIST` |
| `room_type` | Auditoriya turi | `ROOM.FORWHAT` |

- Tizim roʻyxatlari (yuqoridagi uchtasi) ilova ichida kod boʻyicha qidiriladi, shuning uchun ularning roʻyxat kodlarini oʻzgartirib yoki oʻchirib boʻlmaydi. Qiymatlarni esa erkin qoʻshish mumkin.
- Roʻyxatni oching va pastdagi **Kodlar** boʻlimida qiymat qoʻshing. Kodlar kichik lotin harflari, raqamlar va pastki chiziqdan iborat boʻladi (masalan, `korean`). Nomni har bir til uchun kiriting; inglizcha nom majburiy.
- Endi ishlatilmaydigan qiymatlarni oʻchirmang, buning oʻrniga **Faol** belgisini oʻchiring. Qiymat maʼlumotlarda hali ishlatilayotgan boʻlsa, uni oʻchirib boʻlmaydi.
- Koʻp qiymatlarni [CSV import](09-csv-import.md) orqali kiriting.

## Davlatlar va tillar

ISO standarti roʻyxatlari (249 ta davlat, 180 ga yaqin til) oʻrnatish paytida yuklanadi. Nomlar oʻrnatilgan tillar uchun avtomatik toʻldiriladi.

- Ekranda koʻrsatiladigan nomni oʻzgartirish uchun uni **Tahrirlash** orqali oʻzgartiring. Oʻzgartirilgan nom keyingi tizim yangilanishlarida ham saqlanib qoladi.
- Yozuvni tanlash roʻyxatlaridan yashirish uchun **Faol** belgisini oʻchiring.
