# Talabalar axborot tizimi qoʻllanmasi (Oʻzbekcha)

Tizimni har kuni boshqaradigan xodimlar hamda uni oʻrnatadigan, joriy etadigan va xizmat koʻrsatadigan IT operatorlari uchun. Ekranlar oʻzbek tilida mavjud (til menyusi).

Boshqa tillar: [English](../en/README.md), [한국어](../ko/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md), [Deutsch](../de/README.md), [Filipino](../fil/README.md), [Français](../fr/README.md), [日本語](../ja/README.md), [Монгол](../mn/README.md), [Bahasa Melayu](../ms/README.md), [नेपाली](../ne/README.md), [Русский](../ru/README.md), [ไทย](../th/README.md), [Türkçe](../tr/README.md), [Tiếng Việt](../vi/README.md). Asl manba koreys tilidagi nashr; qolgan nashrlar ona tili sohiblari tomonidan tekshirilishi kutilayotgan tarjimalardir.

## Administrator qoʻllanmasi

[admin/README.md](admin/README.md) — 1–28-boblar: ishni boshlash, foydalanuvchilar va rollardan tortib muassasani sozlash, qabul, fanlarga yozilish, baholar, maʼlumotnomalar, bitiruv va LMS integratsiyasigacha.

## Ekspluatatsiya

| Fayl | Mazmuni |
|---|---|
| [installation.md](operations/installation.md) | Talablar, maʼlumotlar bazasi rollari, muhit sozlamalari, birinchi oʻrnatish va yangilash |
| [deployment-checklist.md](operations/deployment-checklist.md) | Python va gunicorn sozlamalari, production muhit oʻzgaruvchilari, joriy etish tartibi, muntazam tekshiruvlar |
| [commands.md](operations/commands.md) | Barcha boshqaruv buyruqlari (`uv run manage.py ...`) boʻyicha maʼlumotnoma: parametrlar, audit yozuvlari, chiqish kodlari, misollar |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | Uzoq ishlaydigan jarayonlar (Celery worker, beat), rejalashtirilgan vazifalar va navbat vazifalari, nosozliklarni aniqlash (Flower) |
| [backup-restore.md](operations/backup-restore.md) | Nimani zaxiralash kerak, dump va tiklash misollari, tiklash mashqlari |
| [security-keys.md](operations/security-keys.md) | Uchta maxfiy kalit, ularni saqlash, shaxsiy maʼlumotlar kalitini almashtirish |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | Audit xesh zanjiri, saqlash muddati va tozalash, fayllarni tozalash, holat tekshiruvi |
| [load-testing.md](operations/load-testing.md) | Fanlarga yozilish choʻqqisi uchun yuklama testi (Locust) va workerlar soni boʻyicha qaror |
| [troubleshooting.md](operations/troubleshooting.md) | Koʻp uchraydigan alomatlar, nimani tekshirish kerak, soʻrovlar boʻyicha kuzatuv |

## Boshqa hujjatlar

- [LMS integratsiyasi qoʻllanmasi](../../lms-integration-guide.md): API va LMS konnektorlari (dasturchilar uchun)
- [Til qoʻshish](../../development/adding-a-language.md), [nomlash qoidalari](../../development/naming.md), [koʻrib chiqish roʻyxati](../../development/review-checklist.md) (dasturchilar uchun)
- [Hujjatlar mundarijasi](../../README.md)
