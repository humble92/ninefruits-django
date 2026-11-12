# Kalitlarni boshqarish

- Kim uchun: IT operatorlari
- Bogʻliq: [oʻrnatish](installation.md), [buyruqlar maʼlumotnomasi](commands.md), [joriy etish nazorat roʻyxati](deployment-checklist.md)

| Kalit | Vazifasi | Yoʻqolsa | Almashtirish |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Sessiyalar, CSRF, imzolash (parolni tiklash havolalari, e-pochtani tasdiqlash havolalari, eslab qolingan qurilma cookie fayllari), e-pochta orqali ikki bosqichli autentifikatsiya kodlari xeshlari, ikki bosqichli autentifikatsiya sirlarini (autentifikator TOTP sirlari, tiklash kodlari) va SSO mijoz sirlarini shifrlash | Barcha foydalanuvchilar tizimdan chiqariladi, yuborilgan havolalar ishlamay qoladi, ulangan autentifikator ilovalari va tiklash kodlari ishlamay qoladi (har bir foydalanuvchi uchun ikki bosqichli autentifikatsiyani tiklash kerak), SSO mijoz sirlarini qayta kiritish kerak | Oldingi kalitni `DJANGO_SECRET_KEY_FALLBACKS` ga qoʻyib almashtiring (quyidagi tartib) |
| `PII_ENCRYPTION_KEY` | JShShIR kabi shaxsiy maʼlumotlarni shifrlash (AES-256-GCM) | **Shifrlangan shaxsiy maʼlumotlarni tiklab boʻlmaydi** | Oldingi kalitni `PII_PREVIOUS_KEYS` ga qoʻyib almashtiring (quyidagi tartib) |
| `PII_HASH_KEY` | Shaxsiy maʼlumotlar boʻyicha aniq moslik qidiruvi uchun xeshlar (HMAC-SHA256) | Qidiruv ishlamay qoladi (maʼlumotlar saqlanib qoladi) | Odatda almashtirilmaydi |

`DJANGO_SECRET_KEY` ni `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` bilan, ikkita shaxsiy maʼlumotlar kalitini esa `uv run manage.py pii_generate_key` bilan yarating.

Saqlash tamoyillari

- Uchala kalitning kamida ikki nusxasini server sozlamalaridan tashqarida, maxfiy maʼlumotlar omborida (Vault, bulutli maxfiy maʼlumotlar menejeri va h.k.) yoki muhrlangan oflayn omborda saqlang.
- Ularni zaxira fayllar bilan birga saqlamang. Sizib chiqqan MB zaxirasini kalitlarsiz oʻqib boʻlmasligi kerak.
- Ishlab chiqish muhitidagi `.env` yoki test sozlamalaridagi kalitlarni hech qachon production da ishlatmang.
- Veb-jarayonlar (gunicorn), Celery workerlari va Celery beat bir xil kalit qiymatlarini oʻqishi kerak. Kalitni oʻzgartirgandan keyin uchalasini birga qayta ishga tushiring.

## `DJANGO_SECRET_KEY` ni almashtirish

Buni rejali almashtirish uchun yoki kalitni biladigan shaxslar oʻzgarganda ishlating. U Djangoning `SECRET_KEY_FALLBACKS` ga tayanadi, shuning uchun oldingi kalit saqlanib turganda hech kim tizimdan chiqarilmaydi. Bu asl tizimdagi (Laravel) `APP_PREVIOUS_KEYS` bilan bir xil yondashuv.

1. Yangi kalit yarating: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`.
2. Joriy kalitni `DJANGO_SECRET_KEY_FALLBACKS` ning boshiga (bir nechta boʻlsa vergul bilan ajratib), yangi kalitni esa `DJANGO_SECRET_KEY` ga qoʻying.
   ```
   DJANGO_SECRET_KEY=<new key>
   DJANGO_SECRET_KEY_FALLBACKS=<previous key>
   ```
3. gunicorn, Celery workerlari va beat ni qayta ishga tushiring (Docker: `docker compose restart app worker beat`).
4. Ikki bosqichli autentifikatsiya sirlari va SSO mijoz sirlarini yangi kalit bilan qayta shifrlang. Sonini `uv run manage.py security_reencrypt_secrets --dry-run` bilan tekshiring, uni `--dry-run` siz ishga tushiring, soʻngra `--dry-run` 0 ni koʻrsatishini tasdiqlang. Agar oldingi kalit bu qadamdan oldin olib tashlansa, autentifikator ilovalari va tiklash kodlari ishlamay qoladi.
5. Oldingi kalitni qancha vaqt saqlashni hal qiling. Quyidagilar faqat u saqlanib turganda amal qiladi:

   | Band | Oldingi kalit saqlanib turganda | U olib tashlangandan keyin |
   |---|---|---|
   | Kirish sessiyalari | Almashtirishdan keyingi birinchi soʻrovda yangi kalitga oʻtkaziladi | Faqat shu orada ishlatilmagan sessiyalar tizimdan chiqariladi |
   | Parolni tiklash havolalari, e-pochtani tasdiqlash havolalari | Amal qiladi (3 kun) | Qaytadan soʻrash kerak |
   | Eslab qolingan qurilma cookie fayllari | Amal qiladi (xavfsizlik sozlamalaridagi eslab qolish muddati, standart 30 kun) | Keyingi kirishda ikki bosqichli autentifikatsiya yana soʻraladi |
   | E-pochta orqali ikki bosqichli autentifikatsiya kodlari | Almashtirishdan oldin yuborilgan kodlar mos kelmaydi (10 daqiqa amal qiladi) | Xuddi shunday |

   Uni kamida 3 kun yoki eslab qolingan qurilmalarni saqlash uchun eslab qolish muddati davomida saqlang.
6. Muddat tugagach, oldingi kalitni `DJANGO_SECRET_KEY_FALLBACKS` dan olib tashlang va 3-qadamdagidek qayta ishga tushiring.
7. Oldingi kalitni zaxiralarni saqlash muddati davomida muhrlangan holda saqlang. Eski zaxiralardagi ikki bosqichli autentifikatsiya sirlari u bilan shifrlangan. Eski zaxirani tiklashda bu kalitni `DJANGO_SECRET_KEY_FALLBACKS` ga qoʻying va 4-qadamni bajaring.

### Agar kalit sizib chiqqan boʻlsa

1. 1–4-qadamlarni darhol bajaring (oldingi kalit faqat 4-qadamdagi qayta shifrlash uchun kerak).
2. 4-qadam tugashi bilanoq oldingi kalitni olib tashlang va qayta ishga tushiring. Barcha sessiyalar tugaydi, yuborilgan havolalar va eslab qolingan qurilmalar yaroqsiz boʻladi (koʻzlangan natija).
3. Sizib chiqish davridagi kirishlar va maʼmuriy ishlarni xavfsizlik jurnalida koʻrib chiqing ([audit va texnik xizmat](audit-and-maintenance.md)).

## Shaxsiy maʼlumotlar kalitini almashtirish

1. `uv run manage.py pii_generate_key` bilan yangi kalit yarating (natijadan faqat `PII_ENCRYPTION_KEY` dan foydalaning).
2. Joriy kalitni `PII_PREVIOUS_KEYS` ga (bir nechta boʻlsa vergul bilan ajratib), yangi kalitni esa `PII_ENCRYPTION_KEY` ga qoʻying.
3. Jarayonlar sozlamalarni qayta oʻqishi uchun gunicorn va Celery workerlarini qayta ishga tushiring (Docker: `docker compose restart app worker beat`).
4. Shaxsiy maʼlumotlarga ega har bir model uchun `uv run manage.py pii_reencrypt {app.Model} --dry-run` bilan yozuvlar sonini tekshiring (masalan, `person.Person`), soʻngra uni `--force` siz ishga tushiring (tasdiqlash soʻroviga javob bering).
5. Flower vazifalar tugaganini koʻrsatgach va `--dry-run` 0 ni koʻrsatgach, oldingi kalitni `PII_PREVIOUS_KEYS` dan olib tashlang.
6. Oldingi kalitni zaxiralarni saqlash muddati davomida muhrlangan holda saqlang (eski zaxiralarni tiklash uchun kerak boʻladi).

`PII_HASH_KEY` oʻzgartirilsa, saqlangan barcha qidiruv xeshlari notoʻgʻri boʻlib qoladi, shuning uchun JShShIR yoki pasport raqami boʻyicha aniq moslik qidiruvlari ishlamaydi. Odatda u almashtirilmaydi.
