# Anahtar yönetimi

- Hedef kitle: BT operatörleri
- İlgili: [kurulum](installation.md), [komut başvurusu](commands.md), [dağıtım kontrol listesi](deployment-checklist.md)

| Anahtar | Amaç | Kaybolursa | Yenileme |
|---|---|---|---|
| `DJANGO_SECRET_KEY` | Oturumlar, CSRF, imzalama (parola sıfırlama bağlantıları, e-posta doğrulama bağlantıları, hatırlanan cihaz çerezleri), e-posta iki adımlı doğrulama kodu karmaları, iki adımlı doğrulama sırlarının (kimlik doğrulama uygulaması TOTP sırları, kurtarma kodları) ve SSO istemci sırlarının şifrelenmesi | Tüm kullanıcıların oturumu kapanır, gönderilmiş bağlantılar çalışmaz, kurulmuş kimlik doğrulama uygulamaları ve kurtarma kodları çalışmaz hâle gelir (kullanıcı başına iki adımlı doğrulama sıfırlaması gerekir), SSO istemci sırlarının yeniden girilmesi gerekir | Önceki anahtar `DJANGO_SECRET_KEY_FALLBACKS` içindeyken yenileyin (aşağıdaki prosedür) |
| `PII_ENCRYPTION_KEY` | Kimlik numarası gibi kişisel verilerin şifrelenmesi (AES-256-GCM) | **Şifrelenmiş kişisel veriler kurtarılamaz** | Önceki anahtar `PII_PREVIOUS_KEYS` içindeyken yenileyin (aşağıdaki prosedür) |
| `PII_HASH_KEY` | Kişisel verilerde tam eşleşmeli arama için karmalar (HMAC-SHA256) | Arama çalışmaz hâle gelir (veriler kalır) | Kural olarak yenilenmez |

`DJANGO_SECRET_KEY` değerini `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` ile, iki kişisel veri anahtarını `uv run manage.py pii_generate_key` ile oluşturun.

Saklama ilkeleri

- Üç anahtarın en az iki kopyasını sunucu yapılandırması dışında, bir gizli bilgi deposunda (Vault, bir bulut gizli bilgi yöneticisi vb.) veya mühürlü çevrim dışı depolamada tutun.
- Anahtarları yedek dosyalarının yanında saklamayın. Sızan bir veritabanı yedeği anahtarlar olmadan okunamamalıdır.
- Geliştirme `.env` dosyasının veya test ayarlarının anahtarlarını hiçbir zaman üretimde kullanmayın.
- Web süreçleri (gunicorn), Celery worker'ları ve Celery beat aynı anahtar değerlerini okumalıdır. Bir anahtarı değiştirdikten sonra üçünü birlikte yeniden başlatın.

## `DJANGO_SECRET_KEY` yenileme

Bunu planlı yenileme için veya anahtarı bilen kişiler değiştiğinde kullanın. Django'nun `SECRET_KEY_FALLBACKS` özelliğine dayanır; bu nedenle önceki anahtar tutulduğu sürece kimsenin oturumu kapanmaz. Bu, özgün sistemdeki (Laravel) `APP_PREVIOUS_KEYS` ile aynı yaklaşımdır.

1. Yeni bir anahtar oluşturun: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`.
2. Geçerli anahtarı `DJANGO_SECRET_KEY_FALLBACKS` içine ilk sıraya (birden fazlaysa virgülle ayırarak), yeni anahtarı `DJANGO_SECRET_KEY` içine koyun.
   ```
   DJANGO_SECRET_KEY=<new key>
   DJANGO_SECRET_KEY_FALLBACKS=<previous key>
   ```
3. gunicorn'u, Celery worker'larını ve beat'i yeniden başlatın (Docker: `docker compose restart app worker beat`).
4. İki adımlı doğrulama sırlarını ve SSO istemci sırlarını yeni anahtarla yeniden şifreleyin. Sayıları `uv run manage.py security_reencrypt_secrets --dry-run` ile kontrol edin, `--dry-run` olmadan çalıştırın, ardından `--dry-run` komutunun 0 bildirdiğini doğrulayın. Önceki anahtar bu adımdan önce kaldırılırsa kimlik doğrulama uygulamaları ve kurtarma kodları çalışmaz hâle gelir.
5. Önceki anahtarın ne kadar süre tutulacağına karar verin. Aşağıdakiler yalnızca o tutulduğu sürece geçerli kalır:

   | Öğe | Önceki anahtar tutulurken | Kaldırıldıktan sonra |
   |---|---|---|
   | Oturumlar | Yenilemeden sonraki ilk isteklerinde yeni anahtara taşınır | Yalnızca bu arada kullanılmamış oturumlar kapanır |
   | Parola sıfırlama bağlantıları, e-posta doğrulama bağlantıları | Geçerli (3 gün) | Yeniden istenmeleri gerekir |
   | Hatırlanan cihaz çerezleri | Geçerli (güvenlik ayarlarındaki hatırlama süresi, varsayılan 30 gün) | Bir sonraki oturum açmada iki adımlı doğrulama yeniden istenir |
   | E-posta iki adımlı doğrulama kodları | Yenilemeden hemen önce gönderilen kodlar eşleşmez (10 dakika geçerli) | Aynı |

   En az 3 gün veya hatırlanan cihazları korumak için hatırlama süresi boyunca tutun.
6. Süre dolduğunda önceki anahtarı `DJANGO_SECRET_KEY_FALLBACKS` içinden kaldırın ve 3. adımdaki gibi yeniden başlatın.
7. Önceki anahtarı yedek saklama süresi boyunca mühürlü olarak saklayın. Eski yedeklerdeki iki adımlı doğrulama sırları onunla şifrelenmiştir. Eski bir yedeği geri yüklerken o anahtarı `DJANGO_SECRET_KEY_FALLBACKS` içine koyun ve 4. adımı çalıştırın.

### Anahtar sızdıysa

1. 1 ile 4 arasındaki adımları hemen çalıştırın (önceki anahtar yalnızca 4. adımdaki yeniden şifreleme için gereklidir).
2. 4. adım biter bitmez önceki anahtarı kaldırın ve yeniden başlatın. Tüm oturumlar sona erer; gönderilmiş bağlantılar ve hatırlanan cihazlar geçersiz olur (amaçlanan sonuç).
3. Açıkta kalınan süre boyunca yapılan oturum açmaları ve yönetim işlerini güvenlik günlüğünde inceleyin ([denetim ve bakım](audit-and-maintenance.md)).

## Kişisel veri anahtarının yenilenmesi

1. `uv run manage.py pii_generate_key` ile yeni bir anahtar oluşturun (çıktıdan yalnızca `PII_ENCRYPTION_KEY` değerini kullanın).
2. Geçerli anahtarı `PII_PREVIOUS_KEYS` içine (birden fazlaysa virgülle ayırarak), yeni anahtarı `PII_ENCRYPTION_KEY` içine koyun.
3. Süreçlerin yapılandırmayı yeniden okumasını sağlayın: gunicorn'u ve Celery worker'larını yeniden başlatın (Docker: `docker compose restart app worker beat`).
4. Kişisel veri içeren her model için kayıt sayısını `uv run manage.py pii_reencrypt {app.Model} --dry-run` ile kontrol edin (örneğin `person.Person`), ardından `--force` olmadan çalıştırın (onayı yanıtlayın).
5. Flower görevlerin bittiğini gösterdikten ve `--dry-run` 0 bildirdikten sonra önceki anahtarı `PII_PREVIOUS_KEYS` içinden kaldırın.
6. Önceki anahtarı yedek saklama süresi boyunca mühürlü olarak saklayın (eski yedekleri geri yüklemek için gereklidir).

`PII_HASH_KEY` değerini değiştirmek saklanan tüm arama karmalarını yanlış kılar; bu nedenle kimlik veya pasaport numarasına göre tam eşleşmeli aramalar başarısız olur. Kural olarak yenilenmez.
