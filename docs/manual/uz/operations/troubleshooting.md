# Nosozliklarni bartaraf etish

- Kim uchun: IT operatorlari
- Bogʻliq: [joriy etish nazorat roʻyxati](deployment-checklist.md), [rejalashtirilgan vazifalar](scheduled-jobs.md), [buyruqlar maʼlumotnomasi](commands.md)

| Alomat | Nimani tekshirish kerak |
|---|---|
| Tizimga kirgandan soʻng darhol xavfsizlik sahifasiga yoʻnaltiriladi | Ikki bosqichli autentifikatsiya siyosati "majburiy" va imtiyozli muddat tugagan. Foydalanuvchi uni ulagach hal boʻladi. Siyosat **Sozlamalar > Xavfsizlik** boʻlimida |
| Boshqaruv panelida 403 | Foydalanuvchida `admin_panel.access` ruxsatiga (`Boshqaruv panelini ochish`) ega amaldagi rol tayinlash yoʻq. Foydalanuvchini **Foydalanuvchilar va kirish > Foydalanuvchilar** boʻlimida oching va **Rol tayinlashlar** roʻyxatini (muddat, qamrov) tekshiring |
| Menyu bandi yoʻq | Rolda oʻsha ekran uchun ruxsat yoʻq (masalan, `roles.view`) |
| E-pochta kodlari kelmaydi | Pochta sozlamalari (`MAIL_*`, `DEFAULT_FROM_EMAIL`), **Audit > Xavfsizlik hodisalari** dagi `E-pochta kodi yuborildi` yozuvlari, yuborish cheklovlari (har bir foydalanuvchiga daqiqasiga bir marta, soatiga besh marta) |
| Kirish sahifasi `429 Too Many Requests` deb javob beradi | Bitta manzil daqiqasiga `LOGIN_RATE_LIMIT_PER_IP` (standart 30) urinishdan oshib ketgan. Agar bir vaqtda koʻp foydalanuvchi bloklansa, `TRUSTED_PROXY_COUNT` haqiqiy proksilar soniga mos kelishini tekshiring (hamma Nginx manzili sifatida koʻrinadi); kampus NAT ortida qiymatni oshiring ([joriy etish nazorat roʻyxati](deployment-checklist.md#proksilar-va-mijoz-manzili)) |
| Toʻgʻri parol bilan kirib boʻlmaydi | Kirish bloklangan (**xavfsizlik hodisalari** orasida `Kirish bloklandi`) yoki hisob faol emas. Blokni `uv run manage.py security_unlock_user <email> --reason="..."` bilan olib tashlang |
| Ekranda boshqa shaxslar maʼlumotlaridan 0 ta qator koʻrsatiladi | Normal holat boʻlishi mumkin (qatorlar darajasidagi xavfsizlik). **Audit > Maʼlumot oʻzgarishlari** dagi foydalanuvchi ustuniga qarab MB sessiyasi ijrochisi oʻrnatilganini tasdiqlang |
| `400 Bad Request` | Soʻralgan xost nomi `DJANGO_ALLOWED_HOSTS` da yoʻq |
| `403 CSRF verification failed` | `DJANGO_CSRF_TRUSTED_ORIGINS` da `https://` manzili yoʻq yoki Nginx `X-Forwarded-Proto` ni uzatmaydi |
| Cheksiz HTTPS yoʻnaltirishlar | Nginx `X-Forwarded-Proto $scheme` ni uzatmaydi, shuning uchun Django soʻrovni HTTP deb koʻradi (`SECURE_PROXY_SSL_HEADER`) |
| Ekranlar uslublar yoki skriptlarsiz, `manifest.json` xatosi | `npm ci && npm run build` (`static/dist/`), `collectstatic`, Nginx dagi `/static/` location. Production da `VITE_DEV_MODE=false` ishlatiladi |
| Ekranlarning bir qismi ingliz tilida chiqadi | `compilemessages --ignore=.venv` bajarilmagan (`.mo` fayllar yoʻq). Yangi satrlar uchun `uv run manage.py i18n_missing <locale>` |
| `permission denied for schema public` | Ilova `app_runtime` sifatida DDL bajarishga urindi. Migratsiyalarni faqat `uv run manage.py migrate` yoki `setup_install` bilan bajaring (ikkalasi ham avtomatik ravishda `app_migrator` dan foydalanadi) |
| `Audit records are append-only` | Audit jadvalini yangilash yoki oʻchirishga urinish. Bu blokirovka ataylab qilingan |
| PDF yaratish muvaffaqiyatsiz | `uv run manage.py pdf_sample`, Gotenberg holati, `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` |
| Navbat vazifalari tiqilib qolgan | Flower da worker ulanishi va muvaffaqiyatsiz vazifalarni tekshiring, `uv run celery -A config inspect active`, Redis ulanishi (`REDIS_URL`) |
| Rejalashtirilgan vazifalar ishlamaydi, `/api/v1/health/` `degraded` deb javob beradi | Beat toʻxtagan (5 daqiqadan ortiq rejalashtiruvchi heartbeat yoʻq). Beat jarayoni va uning jurnalini tekshiring. Faqat bitta beat |
| Worker jurnalida `Received unregistered task` | Worker hali ham oldingi kodni bajarmoqda. Joriy etgandan keyin workerni qayta ishga tushiring |
| Semestrni yopish tugamaydi | Flower dagi muvaffaqiyatsiz `grading.close_term_records` vazifalari. Sababini bartaraf eting, soʻngra semestrni yopishni qaytadan boshlang (talabalar boʻyicha hisoblashlar qayta bajarilganda bir xil natija beradi) |

Soʻrovlar boʻyicha kuzatuv: `X-Request-Id` javob sarlavhasi qiymati yordamida jurnallar (JSON dagi `request_id`), faoliyat jurnali, maʼlumot oʻzgarishlari va xavfsizlik hodisalarini birgalikda qidirish mumkin. Nginx `X-Request-Id $request_id` ni uzatsa, Nginx kirish jurnali ham qoʻshiladi. Buyruqlarni ishga tushirishda `cmd-` bilan boshlanadigan ishga tushirish ID si ishlatiladi.
