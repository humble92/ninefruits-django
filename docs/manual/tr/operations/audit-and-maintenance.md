# Denetim bütünlüğü ve rutin bakım

- Hedef kitle: BT operatörleri, güvenlik sorumluları
- İlgili: [yönetici kılavuzu 4. bölüm, denetim](../admin/04-audit.md), [komut başvurusu](commands.md), [yedekleme ve geri yükleme](backup-restore.md)

## Denetim karma zinciri

Denetim tabloları (veri değişiklikleri için `audit.record_changes`, iş işlemleri için `audit.activity_log`, güvenlik olayları için `audit.security_events`) yalnızca ekleme yapılabilen tablolardır (tetikleyicilerle zorunlu kılınır). Bunun üzerine, kurcalamayı **ortaya çıkaran** bir mekanizma bulunur.

- Her satıra, eklendiği anda içeriğinin SHA-256 değeri (`row_hash`) verilir.
- `audit_seal` (zamanlanmış iş `audit.seal`, her gün 03:30'da) yeni satırları ID sırasına göre zincire bağlar: `chain_hash = SHA-256(önceki chain_hash || row_hash)`. DB işlevi `audit.seal()` işlevini şema sahibi bağlantısı (`migrator`) üzerinden çağırır.
- `audit_verify_chain`, her satır için içerik karmasını ve zinciri yeniden hesaplar. Tablo başına kontrol edilen satırları, mühürlenen satırları, uyuşmazlıkları ve ilk uyuşmayan kimliği yazdırır; içeriği değişmiş bir satır "row mismatch", eksik ya da sırası değişmiş bir satır "chain mismatch" olarak raporlanır ve komut 2 çıkış koduyla döner.

```bash
uv run manage.py audit_seal
uv run manage.py audit_verify_chain
uv run manage.py audit_verify_chain --table=security_events
```

Dikkat edilmesi gerekenler

- Mühürlenmeden önce (aynı gün içinde) değiştirilen bir satır zincir tarafından yakalanamaz. Bu nedenle mühürleme her gün çalışır; doğrulama ise yedeklemelerden önce ve güvenlik incelemeleri sırasında yapılır.
- Temizleme (`audit_prune`) en eski satırları sildiğinde, kalan ilk satırın bağlantısı kontrol edilmez (silinen aralık, temizleme komutunun denetim kaydında saklanır).
- `app.audit_maintenance = on` ayarını yalnızca DB yöneticisi (şema sahibi `app_migrator`) yapabilir. Uygulama rolünün (`app_runtime`) denetim tablolarında UPDATE veya DELETE yetkisi yoktur.

## Saklama ve temizleme

1. Saklama sürelerini belirleyin (örneğin veri değişiklikleri 3 yıl, iş işlemleri 5 yıl, güvenlik olayları 1 yıl).
2. Temizlemeden önce yedek alın ([yedekleme ve geri yükleme](backup-restore.md)) ve `audit_verify_chain` ile zincirin sağlam olduğunu doğrulayın.
3. Sayıları `uv run manage.py audit_prune --before=YYYY-MM-DD --table=record_changes --dry-run` ile kontrol edin, ardından `--dry-run` olmadan çalıştırın (işlemi yapanın hesabını `--actor=` ile kaydedin). Mühürlenmemiş satırlar hiçbir zaman silinmez; bu nedenle önce `audit_seal` çalıştırın.
4. Temizlemeden sonra `audit_verify_chain` komutunu yeniden çalıştırın.

Temizleme işleminin kendisi de kaydedilir: her çalıştırma, işlem günlüğüne (günlük `command`) kesim tarihini, seçenekleri, işlemi yapan kişiyi ve işletim sistemi kullanıcısını, ayrıca tablo başına **silinen satır sayısını, silinen ID aralığını ve sınırdaki chain_hash değerini** yazar; gerçek bir silme ayrıca `audit.pruned` güvenlik olayı olarak kaydedilir (**Denetim > Güvenlik olayları**). Bu kayıt satırı da bir sonraki mühürlemede zincire bağlanır. `audit_verify_chain` komutunun kalan ilk satırın bağlantısını kontrol etmemesinin nedeni tam da bu sınırdır; sınır karmasını temizleme kaydıyla karşılaştırarak silinen aralığın kayıtlı bir temizlemeyle eşleştiğini doğrulayabilirsiniz.

## Dosya temizliği

`uv run manage.py media_prune_orphans --dry-run`, sahibi artık bulunmayan medya satırlarını ve satırı olmayan dizinleri (`PRIVATE_MEDIA_ROOT/<media id>/`) listeler; `--dry-run` olmadan bunları siler. Kişi fotoğraflarını, başvuru evraklarını, belge PDF'lerini ve sınav kanıtlarını kapsar. Ayda bir veya toplu bir silme işleminden sonra çalıştırın.

## Sistem sağlığı kontrolleri

| Kontrol | Nasıl | Başarısız olduğunda |
|---|---|---|
| Hizmet durumu | `GET /api/v1/health/` (oturum açmadan, yük dengeleyiciler ve izleme için) | DB veya önbellek yanıt vermediğinde `unavailable` (503), zamanlayıcı sinyali 5 dakikadan eskiyse `degraded` (200), aksi hâlde `ok`. `Yönetim paneline erişme` yetkisiyle oturum açılmışsa her kontrolü (`database`, `cache`, `scheduler`) de gösterir |
| Tam kontrol | `uv run manage.py system_health_check [--json]` | 12 kontrol: anahtarlar, DB rolleri, RLS, migration'lar, yetki kataloğu, Redis, Celery worker'ları, Gotenberg, depolama, beat sinyali. Herhangi biri başarısız olursa çıkış kodu 2 |
| Üretim ayarları | `uv run manage.py check --deploy` | `DEBUG`, HTTPS yönlendirmeleri, HSTS, güvenli çerezler, gizli anahtar hakkında uyarılar |
| Migration'lar | `uv run manage.py migrate --check` | Uygulanmamış migration varsa çıkış kodu 1 |
| Yetki kataloğu | `uv run manage.py security_sync_permissions` | Koddaki yetki listesini DB'ye aktarır (yeniden çalıştırmak güvenlidir) |
| PDF hizmeti | `uv run manage.py pdf_sample` | Gotenberg bağlantısı, yazı tipleri |
| Çeviriler | `uv run manage.py i18n_missing --strict` | Eksik çeviri varsa çıkış kodu 2 |
| Denetim zinciri | `uv run manage.py audit_verify_chain` | Uyuşmazlıkta çıkış kodu 2 |
| Kuyruk | Flower, `uv run celery -A config inspect ping` | Worker yanıt vermiyor |

İzlemeyi HTTP durumuna ve `/api/v1/health/` yanıtındaki `status` değerine bağlayın; diğerlerini dağıtım sırasında ve [rutin kontrollerde](deployment-checklist.md#rutin-kontroller) çalıştırın.
