# Yedekleme ve geri yükleme

- Hedef kitle: BT operatörleri
- İlgili: [kurulum](installation.md), [anahtar yönetimi](security-keys.md), [denetim bütünlüğü](audit-and-maintenance.md)

## Neyin yedekleneceği

| Hedef | Yöntem | Sıklık (önerilen) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` veya PITR (WAL arşivleme) | Günlük tam yedek + sürekli WAL |
| Özel dosya deposu (`PRIVATE_MEDIA_ROOT`, varsayılan `storage/private`) | Anlık görüntü veya sürümlü bucket | DB ile aynı |
| Ortam yapılandırması ve anahtarlar (`DJANGO_SECRET_KEY`, `PII_*`, DB parolaları) | Gizli bilgi deposu | Her değişiklikte |

DB ve dosya deposu aynı zaman noktasına geri yüklenebilmelidir (fotoğrafların, başvuru evraklarının, belge PDF'lerinin ve sınav kanıtlarının meta verileri `media` DB tablosunda tutulur). Redis yedeklenmez: yalnızca önbelleği, kilitleri ve kuyruğu tutar; oturumlar da DB'de (`django_session`) saklanır. Zamanlanmış işlerin listesi (django-celery-beat) de DB'dedir ve beat başlarken onu `config/celery.py` ile yeniden hizalar.

`staticfiles/` ve `static/dist/` derleme çıktısıdır ve yedeklenmez (`npm run build` ve `collectstatic` onları yeniden oluşturur).

## DB yedekleme örneği

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` her şemanın (`public`, `audit`, `reporting`, `util`) sahibidir; bu nedenle yedeği bu hesapla alın. Roller (`app_*`) küme nesneleridir ve dökümün parçası değildir. Geri yükleme sunucusunda önce rolleri [Kurulum](installation.md) belgesinin 2. bölümünde anlatıldığı gibi oluşturun.

Yedeklemeden önce `uv run manage.py audit_verify_chain` çalıştırırsanız, aynı komutu geri yüklenen DB üzerinde çalıştırarak denetim zincirlerini karşılaştırabilirsiniz.

## Geri yükleme örneği

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

Uygulamayı geri yüklenen DB üzerinde çalıştırmak için `DB_DATABASE=ninefruits_restore` değerini ve **yedek alındığı andaki anahtarları** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY` ve o zamandan beri bir anahtar yenilendiyse `PII_PREVIOUS_KEYS`) ayarlayın. Ardından durumu kontrol edin:

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

`migrate --check` uygulanacak migration'lar bildirirse yedek mevcut koddan eskidir. Aynı sürümün koduyla geri yükleyin veya `setup_install --force` ile yükseltin.

## Geri yükleme tatbikatları

Her çeyrekte ayrı bir sunucuya geri yükleyin ve şunları doğrulayın: oturum açma, kişisel verilerin şifresinin çözülmesi (yönetim panelinde bir kişide **Kimlik numarasını göster**; anahtarlar eşleşiyor), denetim kayıtlarının görüntülenmesi ve `audit_verify_chain`, dosyaların açılması (fotoğraflar, belge PDF'leri), belge doğrulama sayfası. Sonucu (geçen süre, sorunlar) kaydedin.
