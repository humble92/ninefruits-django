# Rejalashtirilgan vazifalar va navbatlar

- Kim uchun: IT operatorlari
- Bogʻliq: [joriy etish nazorat roʻyxati](deployment-checklist.md), [audit yaxlitligi](audit-and-maintenance.md), [buyruqlar maʼlumotnomasi](commands.md)

## Uzoq ishlaydigan jarayonlar

| Jarayon | Buyruq | Tekshirish |
|---|---|---|
| Veb | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| Navbat ishlovchisi (worker) | `uv run celery -A config worker --loglevel=INFO` | Flower dagi **Workers**, `uv run celery -A config inspect ping` |
| Rejalashtiruvchi | `uv run celery -A config beat --loglevel=INFO` (**butun tizimda aynan bitta jarayon**) | `/api/v1/health/` dagi `scheduler`, beat jurnali |
| Navbat monitori (ixtiyoriy) | `uv run celery -A config flower --port=5555` | Faqat ichki tarmoqda yoki Nginx kirish cheklovi ortida |

Uchalasi ham bir xil kod va muhit oʻzgaruvchilaridan foydalanadi. systemd misoli:

```ini
# /etc/systemd/system/ninefruits-celery.service
[Service]
User=ninefruits
WorkingDirectory=/srv/ninefruits
EnvironmentFile=/etc/ninefruits/env
ExecStart=/usr/local/bin/uv run --no-sync celery -A config worker --loglevel=INFO
KillSignal=SIGTERM
TimeoutStopSec=300
Restart=always
```

Beat uchun `ExecStart=... celery -A config beat --loglevel=INFO` bilan xuddi shunday yana bitta xizmat yarating. Bir nechta server boʻlsa ham, beat xizmatini faqat bittasida yoqing.

## Rejalashtirilgan vazifalar

Roʻyxatdan oʻtkazishlar `config/celery.py` dagi `beat_schedule` da joylashgan; beat ishga tushganda django-celery-beat maʼlumotlar bazasi rejalashtiruvchisini (`django_celery_beat_*` jadvallari) unga moslashtiradi. Vaqtlar server vaqt mintaqasida (`APP_TIMEZONE`, standart UTC). Har bir rejalashtirilgan vazifa Redis qulfini (`single_instance`) ushlab turadi, shuning uchun bir xil vazifa hech qachon bir vaqtda ikki marta bajarilmaydi.

| Vazifa (Celery nomi) | Davriylik | Xuddi shu ishni bajaradigan buyruq | Nosozlikni aniqlash |
|---|---|---|---|
| `admission.expire_drafts` | Har kuni 03:10 da | `admission_expire_drafts` | Buyruqning oʻzini bajaradi, shuning uchun har bir ishga tushirish faoliyat jurnaliga (log `command`) yoziladi. Bir kundan ortiq yozuv boʻlmasa, beat va workerni tekshiring |
| `registration.release_reserved_seats` | Har 5 daqiqada | `registration_release_reserved_seats` | Audit yozuvi yoʻq. Boʻshatish vaqti oʻtgan oʻrin taqsimotlarida `release_processed_at` hali ham boʻsh boʻlsa, beat ni tekshiring |
| `registration.promote_waitlists` | Har soatda, soat boshida | `waitlist_promote` | Faoliyat jurnalida yozuv yoʻq (oʻtkazilgan fanga yozilishlar maʼlumot oʻzgarishlarida `system:task:registration.promote_waitlists` sifatida koʻrinadi). Flower dagi vazifa natijasi (fan guruhlari, oʻtkazishlar) |
| `lms.reconcile` | Har kuni 02:30 da | `lms_reconcile` | Har bir bogʻlanish boʻyicha sinxronlash yozuvlari (boshqaruv panelidagi **LMS integratsiyasi**), Flower dagi vazifa natijasi |
| `audit.seal` | Har kuni 03:30 da | `audit_seal` | Audit xesh zanjirini muhrlaydi ([audit yaxlitligi](audit-and-maintenance.md)). `audit_verify_chain` bir kunlikdan koʻp muhrlanmagan qatorlarni koʻrsatsa, tekshiring |
| `core.heartbeat` | Har daqiqada | Yoʻq | Oxirgi ishga tushirish vaqtini `system:heartbeat` kesh kalitiga yozadi. U 5 daqiqadan eski boʻlsa, `/api/v1/health/` `degraded` deb javob beradi |

## Navbat vazifalari

| Vazifa (Celery nomi) | Nima ishga tushiradi | Izohlar |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | Har bir yozuvlar paketi uchun bitta vazifa (group). Paket muvaffaqiyatsiz boʻlsa, buyruqni qayta ishga tushiring (joriy kalitdagi yozuvlar oʻtkazib yuboriladi) |
| `registration.promote_waitlist` | Fandan chiqish yoki voz kechish, oʻrin taqsimotini boʻshatish | Har bir fan guruhi uchun faqat bittasi ishlaydi (Redis qulfi, takrorlanishning oldi olinadi). Kutish roʻyxatidan oʻtkazishda barcha fanga yozilish qoidalari qayta tekshiriladi. Tranzaksiya yakunlangandan keyin navbatga qoʻyiladi |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, boshqaruv panelida semestrni yopish | Chord: 100 talabadan iborat vazifalar, ulardan keyin yakunlovchi vazifa (imtiyozlar reytingi, semestr holatini oʻzgartirish, uni boshlagan xodimni xabardor qilish). Jarayon `term-close:{term code}` nomli `job_batches` qatori boʻlib, boshqaruv panelida koʻrsatiladi. Paket vazifasi maʼlumotlar bazasi xatolarida 3 martagacha qayta urinadi; baribir muvaffaqiyatsiz boʻlsa, butun paket muvaffaqiyatsiz deb belgilanadi va yakunlovchi vazifa bajarilmaydi. Sababini bartaraf eting, soʻngra semestrni yopishni qaytadan boshlang (talabalar boʻyicha hisoblashlar qayta bajarilganda bir xil natija beradi) |
| `importing.import_chunk` | Boshqaruv panelidagi CSV import, `reference_import` | Har bir boʻlak uchun bitta vazifa. Natijalar `imports` da, xatoli qatorlar `failed_import_rows` da (boshqaruv panelidagi import natijalari) |
| `lms.sync_section`, `lms.sync_enrollment` | Fan guruhi va fanga yozilish oʻzgarishi hodisalari | Muvaffaqiyatsiz boʻlsa, bir daqiqa oraliq bilan 3 martagacha qayta uriniladi. Qolganini tungi `lms.reconcile` tuzatadi |

Vazifa bajarilayotganda MB ijrochisi `system:task:{task name}` sifatida (masalan, `system:task:grading.close_term_records`), uni navbatga qoʻygan soʻrovning soʻrov ID si va foydalanuvchisi bilan birga qayd etiladi.

Flower muvaffaqiyatsiz vazifalarni (**Tasks**, holat `FAILURE`) va ularning istisnolarini koʻrsatadi. Celery vazifalari `acks_late` dan foydalanadi, shuning uchun worker toʻxtab qolishi sababli uzilgan vazifa qayta bajariladi. Har bir vazifa qayta bajarilganda bir xil natija beradigan qilib tuzilgan (idempotent).
