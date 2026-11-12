# Öğrenci bilgi sistemi kılavuzu (Türkçe)

Sistemi günlük olarak yöneten personel ile sistemi kuran, dağıtan ve bakımını yapan BT operatörleri içindir. Ekranlar Türkçe olarak kullanılabilir (dil menüsü).

Diğer diller: [English](../en/README.md), [한국어](../ko/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md), [Deutsch](../de/README.md), [Filipino](../fil/README.md), [Français](../fr/README.md), [日本語](../ja/README.md), [Монгол](../mn/README.md), [Bahasa Melayu](../ms/README.md), [नेपाली](../ne/README.md), [Русский](../ru/README.md), [ไทย](../th/README.md), [Oʻzbek](../uz/README.md), [Tiếng Việt](../vi/README.md). Kaynak metin Korecedir; diğer sürümler, ana dili konuşan kişilerin incelemesini bekleyen çevirilerdir.

## Yönetici kılavuzu

[admin/README.md](admin/README.md) — 1. ile 28. bölümler arası: başlangıç, kullanıcılar ve roller, kurum ayarları, öğrenci kabul, ders kaydı, notlar, belgeler, mezuniyet ve LMS entegrasyonu.

## İşletim

| Dosya | İçerik |
|---|---|
| [installation.md](operations/installation.md) | Gereksinimler, veritabanı rolleri, ortam yapılandırması, ilk kurulum ve güncellemeler |
| [deployment-checklist.md](operations/deployment-checklist.md) | Python ve gunicorn ayarları, üretim ortam değişkenleri, dağıtım prosedürü, rutin kontroller |
| [commands.md](operations/commands.md) | Tüm yönetim komutlarının (`uv run manage.py ...`) başvuru kaynağı: seçenekler, denetim kayıtları, çıkış kodları, örnekler |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | Sürekli çalışan süreçler (Celery worker, beat), zamanlanmış işler ve kuyruk işleri, hataların nasıl tespit edileceği (Flower) |
| [backup-restore.md](operations/backup-restore.md) | Neyin yedekleneceği, döküm ve geri yükleme örnekleri, geri yükleme tatbikatları |
| [security-keys.md](operations/security-keys.md) | Üç gizli anahtar, nasıl saklanacakları, kişisel veri anahtarının yenilenmesi |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | Denetim karma zinciri, saklama ve temizleme, dosya temizliği, sistem sağlığı kontrolü |
| [load-testing.md](operations/load-testing.md) | Ders kaydı yoğunluğu için yük testi (Locust) ve worker sayısı kararı |
| [troubleshooting.md](operations/troubleshooting.md) | Sık görülen belirtiler, neyin kontrol edileceği, istek bazında izleme |

## Diğer belgeler

- [LMS entegrasyon kılavuzu](../../lms-integration-guide.md): API ve LMS bağlayıcıları (geliştiriciler)
- [Dil ekleme](../../development/adding-a-language.md), [adlandırma kuralları](../../development/naming.md), [inceleme kontrol listesi](../../development/review-checklist.md) (geliştiriciler)
- [Belge dizini](../../README.md)
