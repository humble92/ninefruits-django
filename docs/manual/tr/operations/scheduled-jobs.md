# Zamanlanmış işler ve kuyruklar

- Hedef kitle: BT operatörleri
- İlgili: [dağıtım kontrol listesi](deployment-checklist.md), [denetim bütünlüğü](audit-and-maintenance.md), [komut başvurusu](commands.md)

## Sürekli çalışan süreçler

| Süreç | Komut | Kontrol |
|---|---|---|
| Web | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| Kuyruk çalışanı | `uv run celery -A config worker --loglevel=INFO` | Flower'da **Workers**, `uv run celery -A config inspect ping` |
| Zamanlayıcı | `uv run celery -A config beat --loglevel=INFO` (**toplamda tam olarak bir süreç**) | `/api/v1/health/` içinde `scheduler`, beat günlüğü |
| Kuyruk izleme (isteğe bağlı) | `uv run celery -A config flower --port=5555` | Yalnızca iç ağda veya bir Nginx erişim kısıtlamasının arkasında |

Üçü de aynı kodu ve ortam değişkenlerini kullanır. Bir systemd örneği:

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

Beat için aynı biçimde bir hizmet daha oluşturun: `ExecStart=... celery -A config beat --loglevel=INFO`. Birden fazla sunucu olsa bile beat hizmetini yalnızca birinde etkinleştirin.

## Zamanlanmış işler

Kayıtlar `config/celery.py` içindeki `beat_schedule` tanımıdır; beat başlarken django-celery-beat veritabanı zamanlayıcısını (`django_celery_beat_*` tabloları) onunla hizalar. Zamanlar sunucu saat dilimindedir (`APP_TIMEZONE`, varsayılan UTC). Her zamanlanmış iş bir Redis kilidi (`single_instance`) tutar; bu nedenle aynı iş hiçbir zaman aynı anda iki kez çalışmaz.

| İş (Celery adı) | Sıklık | Aynı işi yapan komut | Hata tespiti |
|---|---|---|---|
| `admission.expire_drafts` | Her gün 03:10'da | `admission_expire_drafts` | Komutun kendisini çalıştırır; bu nedenle her çalıştırma işlem günlüğüne kaydedilir (günlük `command`). Bir günden uzun süredir kayıt yoksa beat'i ve worker'ı kontrol edin |
| `registration.release_reserved_seats` | 5 dakikada bir | `registration_release_reserved_seats` | Denetim kaydı yoktur. Serbest bırakma zamanı geçmiş kontenjan ayırmalarının `release_processed_at` değeri hâlâ boşsa beat'i kontrol edin |
| `registration.promote_waitlists` | Saatte bir, saat başında | `waitlist_promote` | İşlem günlüğü kaydı yoktur (kayda alınan ders kayıtları veri değişikliklerinde `system:task:registration.promote_waitlists` olarak görünür). Flower'daki görev sonucu (şubeler, kayda almalar) |
| `lms.reconcile` | Her gün 02:30'da | `lms_reconcile` | Bağlantı başına eşitleme kayıtları (yönetim paneli **LMS entegrasyonu**), Flower'daki görev sonucu |
| `audit.seal` | Her gün 03:30'da | `audit_seal` | Denetim karma zincirini mühürler ([denetim bütünlüğü](audit-and-maintenance.md)). `audit_verify_chain` bir günlükten fazla mühürlenmemiş satır gösteriyorsa kontrol edin |
| `core.heartbeat` | Her dakika | Yok | Son çalışma zamanını `system:heartbeat` önbellek anahtarına yazar. 5 dakikadan eskiyse `/api/v1/health/` `degraded` yanıtı verir |

## Kuyruk görevleri

| Görev (Celery adı) | Tetikleyen | Notlar |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | Kayıt grubu başına bir görev (group). Bir grup başarısız olduysa komutu yeniden çalıştırın (zaten geçerli anahtardaki kayıtlar atlanır) |
| `registration.promote_waitlist` | Ders bırakma veya dersten çekilme, kontenjan ayırmasının serbest bırakılması | Şube başına yalnızca biri çalışır (Redis kilidi, mükerrerler önlenir). Bekleme listesinden kayda alma her ders kaydı kuralını yeniden kontrol eder. İşlem (transaction) onaylandıktan sonra kuyruğa alınır |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, yönetim panelinde dönem kapatma | Bir chord: 100 öğrencilik görevler, ardından bitirme görevi (onur sıralaması, dönem durumu değişikliği, başlatan personele bildirim). İlerleme, yönetim panelinde gösterilen `term-close:{term code}` `job_batches` satırıdır. Bir grup görevi veritabanı hatalarında 3 kereye kadar yeniden dener; yine başarısız olursa tüm grup başarısız olarak işaretlenir ve bitirme görevi çalışmaz. Nedeni giderin, ardından dönem kapanışını yeniden başlatın (öğrenci başına hesaplamalar yeniden çalıştırıldığında aynı sonucu verir) |
| `importing.import_chunk` | Yönetim panelinde CSV içe aktarma, `reference_import` | Parça başına bir görev. Sonuçlar `imports` içinde, başarısız satırlar `failed_import_rows` içinde (yönetim panelindeki içe aktarma sonuçları) |
| `lms.sync_section`, `lms.sync_enrollment` | Şube ve ders kaydı değişikliği olayları | Başarısızlıkta birer dakika arayla 3 kereye kadar yeniden denenir. Kalanları gece çalışan `lms.reconcile` düzeltir |

Bir görev çalışırken DB'deki işlemi yapan kişi `system:task:{task name}` olarak kaydedilir (örneğin `system:task:grading.close_term_records`); onu kuyruğa alan isteğin istek kimliği ve kullanıcısı da birlikte kaydedilir.

Flower başarısız görevleri (**Tasks**, durum `FAILURE`) ve istisnalarını gösterir. Celery görevleri `acks_late` kullanır; bu nedenle ölen bir worker tarafından yarıda kesilen görev yeniden çalışır. Her görev yeniden çalıştırıldığında aynı sonucu verecek şekilde (idempotent) tasarlanmıştır.
