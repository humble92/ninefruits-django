# Audit yaxlitligi va muntazam texnik xizmat

- Kim uchun: IT operatorlari, axborot xavfsizligi masʼullari
- Bogʻliq: [administrator qoʻllanmasi, 4-bob, audit](../admin/04-audit.md), [buyruqlar maʼlumotnomasi](commands.md), [zaxiralash va tiklash](backup-restore.md)

## Audit xesh zanjiri

Audit jadvallari (maʼlumot oʻzgarishlari uchun `audit.record_changes`, ish faoliyati uchun `audit.activity_log`, xavfsizlik hodisalari uchun `audit.security_events`) faqat qoʻshishga ruxsat beradi (triggerlar bilan taʼminlanadi). Bundan tashqari, soxtalashtirishni **fosh qiladigan** mexanizm mavjud.

- Har bir qatorga qoʻshilayotganda uning mazmunidan SHA-256 (`row_hash`) hisoblanadi.
- `audit_seal` (rejalashtirilgan vazifa `audit.seal`, har kuni 03:30 da) yangi qatorlarni ID tartibida zanjirga bogʻlaydi: `chain_hash = SHA-256(previous chain_hash || row_hash)`. U sxema egasi ulanishi (`migrator`) orqali MB dagi `audit.seal()` funksiyasini chaqiradi.
- `audit_verify_chain` har bir qator uchun mazmun xeshini va zanjirni qayta hisoblaydi. Har bir jadval boʻyicha tekshirilgan qatorlar, muhrlangan qatorlar, nomuvofiqliklar va birinchi nomuvofiq ID ni chiqaradi; mazmuni oʻzgargan qator "row mismatch", yetishmayotgan yoki tartibi oʻzgargan qator "chain mismatch" sifatida koʻrsatiladi va buyruq 2 chiqish kodini qaytaradi.

```bash
uv run manage.py audit_seal
uv run manage.py audit_verify_chain
uv run manage.py audit_verify_chain --table=security_events
```

Yodda tutish kerak boʻlgan jihatlar

- Muhrlanishdan oldin (oʻsha kunning oʻzida) oʻzgartirilgan qatorni zanjir aniqlay olmaydi. Shu sababli muhrlash har kuni bajariladi, tekshirish esa zaxiralashdan oldin va xavfsizlik tekshiruvlari paytida oʻtkaziladi.
- Tozalash (`audit_prune`) eng eski qatorlarni oʻchirganda, qolgan birinchi qatorning bogʻlanishi tekshirilmaydi (oʻchirilgan oraliq tozalash buyrugʻining audit yozuvida saqlanadi).
- `app.audit_maintenance = on` ni faqat MB administratori (sxema egasi `app_migrator`) oʻrnatishi mumkin. Ilova rolida (`app_runtime`) audit jadvallarida UPDATE yoki DELETE huquqi yoʻq.

## Saqlash muddati va tozalash

1. Saqlash muddatlarini belgilang (masalan, maʼlumot oʻzgarishlari 3 yil, ish faoliyati 5 yil, xavfsizlik hodisalari 1 yil).
2. Tozalashdan oldin zaxira nusxa oling ([zaxiralash va tiklash](backup-restore.md)) va `audit_verify_chain` bilan zanjir buzilmaganini tasdiqlang.
3. `uv run manage.py audit_prune --before=YYYY-MM-DD --table=record_changes --dry-run` bilan sonlarni tekshiring, soʻngra `--dry-run` siz ishga tushiring (operator hisobini `--actor=` bilan qayd eting). Muhrlanmagan qatorlar hech qachon oʻchirilmaydi, shuning uchun avval `audit_seal` ni bajaring.
4. Tozalashdan keyin `audit_verify_chain` ni yana ishga tushiring.

Tozalashning oʻzi ham qayd etiladi: har bir ishga tushirish faoliyat jurnaliga (log `command`) chegara sanasi, parametrlar, ijrochi va OT foydalanuvchisini, shuningdek har bir jadval boʻyicha **oʻchirilgan qatorlar soni, oʻchirilgan ID lar oraligʻi va chegaradagi chain_hash** ni yozadi; haqiqiy oʻchirish qoʻshimcha ravishda `audit.pruned` xavfsizlik hodisasi sifatida ham qayd etiladi (**Audit > Xavfsizlik hodisalari**). Bu yozuv qatorining oʻzi ham keyingi muhrlashda zanjirga bogʻlanadi. Aynan shu chegara sababli `audit_verify_chain` qolgan birinchi qatorning bogʻlanishini tekshirmaydi; chegara xeshini tozalash yozuvi bilan solishtirib, oʻchirilgan oraliq qayd etilgan tozalashga mos kelishini tasdiqlash mumkin.

## Fayllarni tozalash

`uv run manage.py media_prune_orphans --dry-run` egasi endi mavjud boʻlmagan media qatorlarini va qatori yoʻq kataloglarni (`PRIVATE_MEDIA_ROOT/<media id>/`) roʻyxat qilib chiqaradi; `--dry-run` siz ularni oʻchiradi. U shaxslar fotosuratlari, ariza hujjatlari, maʼlumotnoma PDF fayllari va imtihon tasdiqlovchi hujjatlarini qamrab oladi. Uni har oy yoki ommaviy oʻchirishdan keyin ishga tushiring.

## Holat tekshiruvlari

| Tekshiruv | Qanday | Muvaffaqiyatsiz boʻlganda |
|---|---|---|
| Xizmat holati | `GET /api/v1/health/` (tizimga kirishsiz, yuklama muvozanatlagichlari va monitoring uchun) | MB yoki kesh javob bermasa `unavailable` (503), rejalashtiruvchi heartbeat 5 daqiqadan eski boʻlsa `degraded` (200), aks holda `ok`. `Boshqaruv panelini ochish` ruxsati bilan tizimga kirilgan boʻlsa, har bir tekshiruvni ham (`database`, `cache`, `scheduler`) koʻrsatadi |
| Toʻliq tekshiruv | `uv run manage.py system_health_check [--json]` | 12 ta tekshiruv: kalitlar, MB rollari, RLS, migratsiyalar, ruxsatlar katalogi, Redis, Celery workerlari, Gotenberg, saqlash joyi, beat heartbeat. Biror tekshiruv muvaffaqiyatsiz boʻlsa, 2 chiqish kodi |
| Production sozlamalari | `uv run manage.py check --deploy` | `DEBUG`, HTTPS yoʻnaltirishlari, HSTS, xavfsiz cookie fayllari, maxfiy kalit haqida ogohlantirishlar |
| Migratsiyalar | `uv run manage.py migrate --check` | Qoʻllanmagan migratsiyalar boʻlsa, 1 chiqish kodi |
| Ruxsatlar katalogi | `uv run manage.py security_sync_permissions` | Koddagi ruxsatlar roʻyxatini MB ga olib kiradi (qayta ishga tushirish xavfsiz) |
| PDF xizmati | `uv run manage.py pdf_sample` | Gotenberg ulanishi, shriftlar |
| Tarjimalar | `uv run manage.py i18n_missing --strict` | Tarjimalar yetishmasa, 2 chiqish kodi |
| Audit zanjiri | `uv run manage.py audit_verify_chain` | Nomuvofiqlik boʻlsa, 2 chiqish kodi |
| Navbat | Flower, `uv run celery -A config inspect ping` | Worker javob bermaydi |

Monitoringni `/api/v1/health/` ning HTTP holatiga va `status` qiymatiga ulang; qolganlarini joriy etishda va [muntazam tekshiruvlarda](deployment-checklist.md#muntazam-tekshiruvlar) bajaring.
