# Yuklama testi (fanlarga yozilish choʻqqisi)

- Kim uchun: IT operatorlari
- Bogʻliq: [joriy etish nazorat roʻyxati](deployment-checklist.md), [oʻrnatish](installation.md), [buyruqlar](commands.md)

Locust fanlarga yozilishning birinchi ertalabini — koʻp talabalar bir vaqtda bir xil fan guruhlariga intiladigan paytni qayta yaratadi. Skript `loadtest/registration.py` (asl tizimdagi k6 `tests/load/registration.js`), ishga tushirish yordamchisi `loadtest/run.sh`, oʻrinlardan ortiq yozilishni tekshirish esa `loadtest/seat_check.sql`.

[Qoʻllanma mundarijasi](../README.md)

## Tayyorgarlik

1. Faqat yuklama testi uchun maʼlumotlar bazasi yarating (hech qachon production bazasi emas). Rollar va baza [oʻrnatish](installation.md) boʻlimining 2-qismidagidek yaratiladi; soʻngra oʻrnating va katta demoni yuklang. Talaba hisoblari roʻyxati shaxsiy ombordagi (`PRIVATE_MEDIA_ROOT`, standart `storage/private`) `load-accounts.csv` ga yoziladi.

   ```bash
   export DB_DATABASE=nf_load
   uv run manage.py setup_install --profile=korean-university --grade-scale=4.5 --force < /dev/null
   uv run manage.py setup_demo --size=large --seed=42 --student-accounts --force
   ```

2. Fanlarga yozilish muddati ochiq boʻlishi kerak. Demo keyingi semestrning fanlarga yozilish muddatlarini kurslar boʻyicha yaratadi (4-kurs allaqachon ochiq, 3-kurs ikki kundan keyin, 1- va 2-kurslar uch kundan keyin). Barcha kurslar bilan oʻlchash uchun boshqa yozilish muddatlarining boshlanishini semestrning **Tahrirlash** sahifasidagi **Jarayon muddatlari** da oʻtmishga koʻchiring ([administrator qoʻllanmasi, 10-bob](../admin/10-terms.md)) yoki test bazasida superfoydalanuvchi sifatida quyidagini bajaring:

   ```sql
   UPDATE term_windows SET opens_at = now() - interval '1 hour'
    WHERE window_type = 'registration' AND opens_at > now() AND closes_at > now();
   ```

3. Redis va Celery worker ishlab turishi kerak. Oʻrinlar bevosita maʼlumotlar bazasida hal qilinadi, lekin kutish roʻyxatidan oʻtkazish, LMS sinxronlash va bildirishnomalar navbat orqali oʻtadi. Agar Redis boshqa ishlar bilan umumiy boʻlsa, boshqa baza raqamidan foydalaning, masalan `REDIS_URL=redis://127.0.0.1:6379/7`.

## Ishga tushirish

`loadtest/run.sh` gunicorn (`config/gunicorn.py`) va Celery worker ni ishga tushiradi, Locust ni headless rejimda bajaradi, oʻrinlarni tekshiradi va hammasini toʻxtatadi.

```bash
export DB_DATABASE=nf_load DB_POOL=true DB_POOL_MIN=1 DB_POOL_MAX=2 DB_PREPARE_THRESHOLD=2
WORKERS=9 USERS=100 DURATION=1m loadtest/run.sh storage/loadtest/w9-u100
```

Qoʻlda ishga tushirish uchun serverni `TRUSTED_PROXY_COUNT=1` bilan ishga tushiring va Locust ni bajaring:

```bash
TRUSTED_PROXY_COUNT=1 DJANGO_DEBUG=false GUNICORN_WORKERS=9 uv run gunicorn config.wsgi -c config/gunicorn.py
uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \
    --host http://127.0.0.1:8000 --csv storage/loadtest/run
psql -h 127.0.0.1 -U postgres -d nf_load -v term=<term id> -f loadtest/seat_check.sql
```

- Ssenariy: tizimga kirish (`/accounts/login/`) → fanlarga yozilish sahifasi → fan qidirish (HTMX `?partial=results`) → boʻsh oʻrni bor birinchi fan guruhiga yozilish → undan chiqish. Har bir iteratsiya cookie fayllarini tozalaydi va keyingi talaba sifatida kiradi. Toʻlgan fan guruhlari va qoidalar boʻyicha rad etishlar normal natija sifatida hisoblanadi (`registration outcomes`).
- Yozilish va chiqish tugmalari HTMX kabi yuboradi (`HX-Request`); server fanlarga yozilish sahifasiga 302 bilan javob beradi. `enroll` va `drop` vaqtlari shu sahifani ham oʻz ichiga oladi (brauzer `#registration` ni almashtirishdan oldin unga muhtoj).
- Har bir talaba oʻzining `X-Forwarded-For` manzilini yuboradi. Server bitta proksi bosqichi ortida boʻlganda (`TRUSTED_PROXY_COUNT=1`), allauth ning manzil boʻyicha kirish cheklovi haqiqiy kampusdagidek har bir talaba manziliga qoʻllanadi. `ADDRESSES=1` barcha talabalarni bitta manzil (NAT) ortida qayta yaratadi.
- Muhit: `ACCOUNTS` (hisoblar CSV), `SEARCH` (qidiruv matni, standart `GEN`), `ADDRESSES`, `FIRST_ACCOUNT` (birinchi hisob, standart holatda tasodifiy). `run.sh` `WORKERS`, `USERS`, `SPAWN_RATE`, `DURATION`, `TERM_ID`, `PORT` ni qabul qiladi.
- `USERS` ni 100 dan 200 ga, 500 ga oshiring va har bir sahifaning p95 hamda muvaffaqiyatsizlik ulushini kuzating. Chegaralar: fanlarga yozilish sahifasi p95 < 800 ms, yozilish p95 < 1.5 s, muvaffaqiyatsizliklar < 1 %. Chegara bajarilmasa, Locust 1 kodi bilan tugaydi.
- Serverda `pg_stat_activity` dagi ulanishlar soni va qulf kutishlarini (`wait_event_type = 'Lock'`), Celery navbatidagi qoldiqni va CPU toʻyinishini kuzating. Shu serverdagi Locust ham CPU dan foydalanadi, shuning uchun raqamlar quyi chegaradir.

## Dizayn nimani kafolatlaydi

- Oʻrinlar soni fan guruhi qatori qulfi (`SeatAllocator.lock`, `SELECT ... FOR NO KEY UPDATE`) va CHECK cheklovlari bilan himoyalangan, shuning uchun bir vaqtdagi soʻrovlar hech qachon fan guruhiga oʻrinlardan ortiq yozmaydi (`tests/registration/test_concurrent_registration.py`: 16 jarayon, 5 oʻrin). Qulf faqat bir xil fan guruhi oʻrinlari uchun soʻrovlarni bir-birini kutishga majbur qiladi; u fan guruhiga shunchaki havola qiladigan qatorlarning (yozilishga urinishlar, LMS sinxronlash jurnallari) tashqi kalit tekshiruvlarini toʻsmaydi.
- Ishga tushirishdan keyin `loadtest/seat_check.sql` ning toʻrtta soʻrovi hech qanday qator qaytarmasligi kerak (oʻrinlardan ortiq, oʻrin hisoblagichi nomuvofiqligi, oʻrinlar guruhi oʻrinlardan ortiq, fan guruhiga takroriy yozilish).
- Fanlarga yozilish sahifasining soʻrovlar soni yozilishlar, kutish roʻyxati yozuvlari yoki qidiruv natijalari bilan oʻsmaydi (`tests/registration/test_portal_query_count.py`).

## Manzil boʻyicha kirish cheklovi va proksilar

Hisob boʻyicha muvaffaqiyatsiz urinishlar cheklovidan (daqiqasiga 5) tashqari, allauth asl tizimda boʻlmagan **manzil boʻyicha kirish cheklovi** ni (`LOGIN_RATE_LIMIT_PER_IP`, standart `30/m/ip`) qoʻllaydi. Ilova koʻradigan manzil `TRUSTED_PROXY_COUNT` bilan belgilanadi (`ninefruits.core.http.client_ip`).

- Nginx ortida `TRUSTED_PROXY_COUNT=0` (standart) boʻlsa, har bir soʻrov Nginx manziliga ega boʻladi. Bitta NAT manzili orqali chiqadigan kampus ham xuddi shu holat.
- Buni qayta yaratgan ishga tushirish (`ADDRESSES=1`, 100 VU, 1 daqiqa): 4 876 ta kirishdan **faqat 30 tasi muvaffaqiyatli** boʻldi, 4 846 tasi 429 bilan rad etildi (49 % muvaffaqiyatsizlik). Oʻsha daqiqada faqat 20 ta yozilish amalga oshdi. Xuddi shu sharoitda har bir talabaga bitta manzil boʻlganda birorta kirish rad etilmadi.
- Production sozlamalari: `TRUSTED_PROXY_COUNT` ni proksilar soniga oʻrnating (bitta Nginx uchun `1`). Agar talabalarning aksariyati bitta NAT manzilini baham koʻrsa, `LOGIN_RATE_LIMIT_PER_IP` ni choʻqqidagi kirishlar tezligigacha oshiring. Misol: 10 daqiqa ichida 2 000 talaba kirishi bitta manzildan daqiqasiga 200 ta degani, shuning uchun `300/m/ip`. Boʻsh qiymat manzil boʻyicha cheklovni olib tashlaydi (asl tizimdagidek; hisob boʻyicha muvaffaqiyatsiz urinishlar cheklovi qoladi).

## Server sozlamalari boʻyicha qarorlar

- **gunicorn sync workerlari** (`config/gunicorn.py`). `GUNICORN_WORKERS` standart holatda CPU yadrolari × 2 + 1. Oʻtkazish qobiliyati CPU bilan cheklangan edi: 4 yadroda 4, 9 va 16 worker bir xil oʻtkazish qobiliyatini berdi (soniyasiga 23 dan 26 gacha soʻrov). Koʻproq worker faqat maʼlumotlar bazasi ulanishlarini (12 → 36) va qulf kutishlarini (choʻqqi 1 → 12) oshirdi. Yadrolar × 2 + 1 dan oshirmang; koʻproq ilova serverlari bilan gorizontal kengaytiring.
- **Ulanishlar pooli va tayyorlangan soʻrovlar (prepared statements)**: `DB_POOL=true`, `DB_POOL_MIN=1`, `DB_POOL_MAX=2`, `DB_PREPARE_THRESHOLD=2`. Qator darajasidagi xavfsizlik (RLS) siyosatlari sababli soʻrovlarni rejalashtirish sahifaning maʼlumotlar bazasi vaqtining katta qismini tashkil qilardi (fanlarga yozilish sahifasining 31 ta soʻrovi: 51 ms rejalashtirish, 19 ms bajarish). Ulanishlarni qayta ishlatish va server tomonida bogʻlash bilan soʻrovlarni tayyorlash har bir soʻrovni har bir ulanishda bir marta rejalashtiradi. Xuddi shu 4 yadroda oʻtkazish qobiliyati soniyasiga 16.8 dan 25.6 soʻrovgacha, bitta foydalanuvchi uchun fanlarga yozilish sahifasining medianasi 160 ms dan 97 ms gacha yaxshilandi. Serverga workerlar × `DB_POOL_MAX` + Celery parallelligi qadar ulanish kerak, bu PostgreSQL ning `max_connections` qiymatidan kam boʻlishi lozim. Tranzaksiya rejimidagi PgBouncer ortida tayyorlangan soʻrovlardan foydalanib boʻlmaydi: `DB_PREPARE_THRESHOLD=0` ni saqlang. Toʻliq test toʻplami (1 066 test) ushbu sozlamalar bilan oʻtadi.
- **ASGI (asl tizimdagi Octane qarori)**: qabul qilinmadi. Har bir sahifa sinxron view boʻlib, ASGI uni foydasiz ravishda oqimda bajarardi, oʻtkazish qobiliyati esa CPU yadrolariga bogʻliq. Django (PHP-FPM dan farqli ravishda) har bir soʻrov uchun ilovani qayta yuklamaydi, shuning uchun Octane beradigan yutuq allaqachon mavjud; doimiy ulanishlar yutugʻi esa yuqoridagi pool va tayyorlangan soʻrovlardan keladi.
- Tizimga kirish Argon2 xesh tekshiruvi sababli har bir soʻrovga koʻp CPU sarflaydi (bitta foydalanuvchi bilan taxminan 140 ms). Choʻqqida kirishlar toʻplanganda bu xarajat birinchi navbatda oʻtkazish qobiliyatini kamaytiradi.

## 2026-10-24 dagi oʻlchovlar

Muhit: 4 vCPU (Xeon 2.1 GHz, `nproc` = 4), 15 GB RAM, boshqa ishlar bilan umumiy ishlab chiqish mashinasi (test ishga tushirishlari; oʻlchovlar vaqtida load average 7 dan 21 gacha), Locust, gunicorn, PostgreSQL 18 va Redis bitta mashinada. Python 3.14, Django 6.1, gunicorn 26.2, `DJANGO_DEBUG=false`. Demo `--size=large --seed=42` (20 004 talaba, 11 437 talaba hisobi, 416 soniyada yaratilgan), barcha kurslar uchun ochiq 2027-yil bahorgi fanlarga yozilish muddati, 52 ta eʼlon qilingan fan guruhi (2 262 oʻrin). Har biri bir daqiqa, `TRUSTED_PROXY_COUNT=1`, har bir talabaga bitta manzil.

| Shart | Oʻtkazish qobiliyati | Sahifa p95 | Yozilish p95 | Muvaffaqiyatsizliklar | Yozildi / rad etildi | Maks. PG ulanishlari |
|---|---|---|---|---|---|---|
| 2 VU, 9 worker, poolsiz | 5.1 req/s | 200 ms | 640 ms | 0 / 300 | 50 / 0 | 3 |
| 2 VU, 9 worker, pool + tayyorlangan soʻrovlar | 6.2 req/s | 160 ms | 470 ms | 0 / 372 | 62 / 0 | 22 |
| 100 VU, 4 worker, poolsiz | 16.8 req/s | 6.0 s | 11 s | 0 / 1 005 | 52 / 86 | 6 |
| 100 VU, 16 worker, poolsiz | 17.1 req/s | 6.1 s | 11 s | 0 / 1 027 | 60 / 86 | 18 |
| 100 VU, 4 worker, pool + tayyorlangan soʻrovlar | 25.6 req/s | 4.1 s | 7.0 s | 0 / 1 536 | 97 / 155 | 12 |
| 100 VU, 9 worker, pool + tayyorlangan soʻrovlar | 25.4 req/s | 4.5 s | 7.3 s | 0 / 1 523 | 77 / 167 | 22 |
| 100 VU, 16 worker, pool + tayyorlangan soʻrovlar | 23.4 req/s | 4.6 s | 8.4 s | 0 / 1 405 | 131 / 79 | 36 |
| 200 VU, 9 worker, pool + tayyorlangan soʻrovlar | 29.8 req/s | 9.4 s | 14 s | 0 / 1 792 | 66 / 172 | 22 |
| 200 VU, 16 worker, pool + tayyorlangan soʻrovlar | 29.2 req/s | 9.1 s | 14 s | 0 / 1 761 | 53 / 174 | 36 |
| 100 VU, 9 worker, bitta manzil (NAT) | (asosan 429) | 2.0 s | 3.3 s | 4 846 / 9 862 | 20 / 10 | 22 |

Qanday oʻqish kerak

- Hech bir ishga tushirishda (bitta manzilli ishga tushirishdan tashqari) HTTP muvaffaqiyatsizliklari va oʻrinlardan ortiq yozilish boʻlmadi (`seat_check.sql` hech qanday qator qaytarmadi). Rad etishlar — toʻlgan fan guruhlari (`capacity`) va takroriy fanlar (`duplicate_course`, oldingi ishga tushirish oxirida uzilgan iteratsiyalar qoldirgan yozilishlar): normal holat.
- 100 VU dagi bir necha soniyalik kechikishlar soʻrovlar navbatidir. Bitta foydalanuvchi bilan server sahifani taxminan 100 ms da, yozilishni (POST va qaytarilgan sahifa) taxminan 290 ms da qayta ishlaydi; 4 yadroni Locust, PostgreSQL va boshqa ishlar bilan baham koʻradigan bu mashina soniyasiga 25–30 soʻrovdan oshmaydi. Bu mashinada chegaralar (sahifa p95 < 800 ms, yozilish p95 < 1.5 s) 100 VU da bajarilmaydi.
- Qulf kutishlari faqat bir xil fan guruhining oʻrin qulflaridan kelib chiqdi va qisqa boʻldi (bir lahzalik choʻqqi 1 dan 12 gacha, worker koʻp boʻlsa koʻproq). Maʼlumotlar bazasi ulanishlari workerlar × 2 dan oshmadi.
- Fanlarga yozilish choʻqqisini "10 daqiqa ichida har biri 6 tadan soʻrov yuboradigan 2 000 talaba" deb olsak, soniyasiga 20 soʻrov chiqadi. Bu mashina (pool + tayyorlangan soʻrovlar) 25–30 ni bajardi, shuning uchun 8 yadroli alohida ilova serverida zaxira bor. Ishga tushirishdan oldin: xuddi shu skriptni production kabi sozlangan staging muhitida (alohida ilova serveri, Nginx, alohida maʼlumotlar bazasi serveri, boshqa mashinadagi Locust) 200 va 500 VU da bajaring va chegaralarni tasdiqlang.
- Asl tizim (Laravel, Sail ishlab chiqish konteyneri, oʻrnatilgan server) 100 VU da 4 worker bilan 24.7 req/s, 16 worker bilan 34.5 req/s bajargan. Mashinalar farq qiladi, shuning uchun raqamlarni bevosita solishtirib boʻlmaydi.
