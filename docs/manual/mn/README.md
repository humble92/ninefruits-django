# Оюутны мэдээллийн системийн гарын авлага (Монгол)

Системийг өдөр тутам удирддаг ажилтнууд болон түүнийг суулгаж, байршуулж, засвар үйлчилгээ хийдэг МТ-ийн ашиглалтын ажилтнуудад зориулав. Дэлгэцүүд монгол хэл дээр ашиглах боломжтой (хэлний цэс).

Бусад хэл: [English](../en/README.md), [한국어](../ko/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md), [Deutsch](../de/README.md), [Filipino](../fil/README.md), [Français](../fr/README.md), [日本語](../ja/README.md), [Bahasa Melayu](../ms/README.md), [नेपाली](../ne/README.md), [Русский](../ru/README.md), [ไทย](../th/README.md), [Türkçe](../tr/README.md), [Oʻzbek](../uz/README.md), [Tiếng Việt](../vi/README.md). Эх хувь нь солонгос хэл дээр; бусад хувилбарууд нь эх хэлтнүүдийн хяналтыг хүлээж буй орчуулга юм.

## Админы гарын авлага

[admin/README.md](admin/README.md) — 1-ээс 28-р бүлэг: эхлэх, хэрэглэгч ба үүргээс эхлээд байгууллагын тохиргоо, элсэлт, хичээл сонголт, дүн, тодорхойлолт, төгсөлт болон LMS холболт хүртэл.

## Ашиглалт

| Файл | Агуулга |
|---|---|
| [installation.md](operations/installation.md) | Шаардлага, өгөгдлийн сангийн роль, орчны тохиргоо, анхны суулгалт ба шинэчлэл |
| [deployment-checklist.md](operations/deployment-checklist.md) | Python ба gunicorn-ийн тохиргоо, production-ий орчны хувьсагч, байршуулах журам, тогтмол шалгалт |
| [commands.md](operations/commands.md) | Удирдлагын команд бүрийн лавлах (`uv run manage.py ...`): сонголт, аудитын бичлэг, exit code, жишээ |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | Тасралтгүй ажиллах процесс (Celery worker, beat), төлөвлөгдсөн ажил ба дарааллын ажил, алдааг хэрхэн илрүүлэх (Flower) |
| [backup-restore.md](operations/backup-restore.md) | Юуг нөөцлөх, dump ба сэргээлтийн жишээ, сэргээх дадлага |
| [security-keys.md](operations/security-keys.md) | Гурван нууц түлхүүр, тэдгээрийг хэрхэн хадгалах, хувийн мэдээллийн түлхүүр солих |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | Аудитын хэш гинж, хадгалах хугацаа ба цэвэрлэлт, файл цэвэрлэх, эрүүл мэндийн шалгалт |
| [load-testing.md](operations/load-testing.md) | Хичээл сонголтын оргил үеийн ачааллын тест (Locust) ба worker-ийн тооны шийдвэр |
| [troubleshooting.md](operations/troubleshooting.md) | Түгээмэл шинж тэмдэг, шалгах зүйл, хүсэлт тус бүрийг мөрдөх |

## Бусад баримт бичиг

- [LMS холболтын гарын авлага](../../lms-integration-guide.md): API ба LMS холбогчид (хөгжүүлэгчид)
- [Хэл нэмэх](../../development/adding-a-language.md), [нэршлийн дүрэм](../../development/naming.md), [хяналтын жагсаалт](../../development/review-checklist.md) (хөгжүүлэгчид)
- [Баримт бичгийн агуулга](../../README.md)
