# Zaxiralash va tiklash

- Kim uchun: IT operatorlari
- Bogʻliq: [oʻrnatish](installation.md), [kalitlarni boshqarish](security-keys.md), [audit yaxlitligi](audit-and-maintenance.md)

## Nimani zaxiralash kerak

| Obyekt | Usul | Davriylik (tavsiya etiladi) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` yoki PITR (WAL arxivlash) | Har kuni toʻliq + uzluksiz WAL |
| Shaxsiy fayllar ombori (`PRIVATE_MEDIA_ROOT`, standart `storage/private`) | Snapshot yoki versiyalanadigan bucket | MB bilan bir xil |
| Muhit sozlamalari va kalitlar (`DJANGO_SECRET_KEY`, `PII_*`, MB parollari) | Maxfiy maʼlumotlar ombori | Har bir oʻzgarishda |

MB va fayllar omborini bir xil vaqt nuqtasiga tiklash mumkin boʻlishi shart (fotosuratlar, ariza hujjatlari, maʼlumotnoma PDF fayllari va imtihon tasdiqlovchi hujjatlarining metamaʼlumotlari MB dagi `media` jadvalida saqlanadi). Redis zaxiralanmaydi: unda faqat kesh, qulflar va navbat saqlanadi, sessiyalar esa MB da ham saqlanadi (`django_session`). Rejalashtirilgan vazifalar roʻyxati (django-celery-beat) ham MB da, beat esa ishga tushganda uni `config/celery.py` bilan qayta moslashtiradi.

`staticfiles/` va `static/dist/` yigʻish (build) natijasi boʻlib, zaxiralanmaydi (`npm run build` va `collectstatic` ularni qayta yaratadi).

## MB ni zaxiralash misoli

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` barcha sxemalarning (`public`, `audit`, `reporting`, `util`) egasi, shuning uchun zaxiralashni shu hisob bilan bajaring. Rollar (`app_*`) klaster obyektlari boʻlib, dumpga kirmaydi. Tiklash serverida avval rollarni [Oʻrnatish](installation.md) boʻlimining 2-qismida tavsiflanganidek yarating.

Zaxiralashdan oldin `uv run manage.py audit_verify_chain` ni bajarsangiz, tiklangan MB da xuddi shu buyruq audit zanjirlarini solishtirish imkonini beradi.

## Tiklash misoli

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

Ilovani tiklangan MB da ishga tushirish uchun `DB_DATABASE=ninefruits_restore` ni va **zaxiralash vaqtidagi kalitlarni** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY` hamda shundan beri kalit almashtirilgan boʻlsa, `PII_PREVIOUS_KEYS`) oʻrnating. Soʻngra holatni tekshiring:

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

Agar `migrate --check` qoʻllanishi kerak boʻlgan migratsiyalar haqida xabar bersa, zaxira joriy koddan eskiroq. Xuddi shu versiyadagi kod bilan tiklang yoki `setup_install --force` bilan yangilang.

## Tiklash mashqlari

Har chorakda alohida serverga tiklang va quyidagilarni tekshiring: tizimga kirish, shaxsiy maʼlumotlarning shifrdan chiqarilishi (boshqaruv panelida shaxs sahifasidagi **JShShIR ni koʻrsatish**; kalitlar mos kelishi), audit yozuvlarini koʻrish va `audit_verify_chain`, fayllarni ochish (fotosuratlar, maʼlumotnoma PDF fayllari), maʼlumotnomani tekshirish sahifasi. Natijani (sarflangan vaqt, muammolar) qayd eting.
