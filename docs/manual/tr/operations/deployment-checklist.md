# Dağıtım kontrol listesi ve gunicorn ile Python ayarları

- Hedef kitle: BT operatörleri
- İlgili: [kurulum](installation.md), [anahtar yönetimi](security-keys.md), [zamanlanmış işler](scheduled-jobs.md), [yük testi](load-testing.md)

## Python ve bağımlılıklar

- **Python 3.14**'ün en son yama sürümünü kullanın. Konteyner veya sunucu imajları oluştururken Python yama sürümünü sabitlemeyin; en sonuncuyu alın (`Dockerfile` içinde `python:3.14-slim`).
- Python bağımlılıkları `uv.lock` içinde kilitlenmiştir. Üretim kurulumları her zaman `uv sync --frozen --no-dev` kullanır (kilit dosyası uyuşmazsa başarısız olur). Geliştirme araçları (pytest, ruff, mypy, Playwright) hiçbir zaman üretime ulaşmaz.
- Django bir güvenlik sürümü yayımladığında `uv lock --upgrade-package django` ile yükseltin, testleri çalıştırın ve dağıtın. Bağımlılık açıklarını CI'ın yaptığı gibi kontrol edin: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`.
- `uv run manage.py check --deploy` üretim ayarları (`DEBUG`, HTTPS, çerezler, HSTS, gizli anahtar uzunluğu) hakkında uyarır. Her dağıtımda sıfır uyarı olmalıdır.

## gunicorn ve Nginx

| Öğe | Değer | Neden |
|---|---|---|
| gunicorn'u çalıştırma | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, eşzamanlı (sync) worker'lar. Worker sayısı ve bağlantı havuzu boyutu ortam değişkenlerinden gelir; gerekçesi [yük testi](load-testing.md) içindedir |
| gunicorn bağlama adresi | `127.0.0.1:8000` veya bir Unix soketi | gunicorn'u hiçbir zaman doğrudan dışarı açmayın; her zaman Nginx'in arkasına koyun |
| Worker'ı yeniden başlatma | Dağıtımda `HUP` (systemd `reload`) | Süren istekleri tamamlar ve worker'ları yeni kodla değiştirir |
| DB bağlantıları | `DB_POOL=true` ile worker başına bir psycopg bağlantı havuzu (`DB_POOL_MIN`, `DB_POOL_MAX`) | Worker sayısı × `DB_POOL_MAX` + Celery bağlantıları PostgreSQL'in `max_connections` değerinin altında kalmalıdır. Havuza dönen bir bağlantının DB oturumu işlem yapan kişisi temizlenir (`ninefruits.core.pool.reset_connection`) |
| Nginx `client_max_body_size` | `32m` | Başvuru evrakları, sınav kanıtları ve fotoğraf yüklemeleri için üst sınır (uygulamanın 5MB ve 2MB doğrulamasının üzerinde pay bırakarak) |
| Nginx statik dosyaları | `location /static/ { alias <repository>/staticfiles/; }` | `collectstatic` çıktısını Nginx'in kendisi sunar |
| Özel dosyalar | `PRIVATE_MEDIA_ROOT` (varsayılan `storage/private`) dizinini Nginx'te **asla eşlemeyin** | Fotoğraflar, başvuru evrakları ve belge PDF'leri yalnızca yetki denetimi yapan görünümler üzerinden indirilir |
| Nginx başlıkları | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, isteğe bağlı olarak `X-Request-Id $request_id` | İstemci adresi, HTTPS algılama, istek bazında izleme |
| Gotenberg, Redis, PostgreSQL | Yalnızca iç adresler | Hiçbir zaman dışarıya açılmaz |

```nginx
server {
    listen 443 ssl;
    server_name sis.example.ac.kr;
    client_max_body_size 32m;

    location /static/ { alias /srv/ninefruits/staticfiles/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-Id $request_id;
    }
}
```

### Proxy'ler ve istemci adresi

Oturum açma sınırları, API istek sınırları ve denetim kayıtlarındaki IP adresleri `ninefruits.core.http.client_ip` tarafından belirlenen istemci adresini kullanır.

- `TRUSTED_PROXY_COUNT`: uygulamanın önünde `X-Forwarded-For` başlığına ekleme yapan ters proxy sayısı. Tek bir Nginx için `1`, bir yük dengeleyici artı Nginx için `2`. `0` (varsayılan) `REMOTE_ADDR` kullanır. Sağdan bu kadar sıra ötedeki giriş istemci adresidir; daha soldaki girişlere (istemcinin gönderdikleri) asla güvenilmez.
- **Değer gerçek proxy sayısından düşükse**, her kullanıcı Nginx adresinden geliyormuş gibi görünür ve oturum açma sınırı tüm kampüse aynı anda uygulanır. **Daha yüksekse**, uygulama istemcinin gönderdiği bir `X-Forwarded-For` başlığına güvenir ve sınırlar aşılabilir. Dağıtımdan sonra yönetim panelinde **Denetim > Güvenlik olayları** altındaki IP adreslerinin gerçek kullanıcı adresleri olduğunu kontrol edin.
- `LOGIN_RATE_LIMIT_PER_IP`: istemci adresi başına oturum açma denemesi (django-allauth, varsayılan `30/m/ip`). Özgün sistemde böyle bir sınır yoktu. Tüm kampüs tek bir NAT adresinden çıkıyorsa bu değer ilk ders kaydı sabahı için çok düşüktür; artırın (örneğin `300/m/ip`). Boş, adres başına sınır olmadığı anlamına gelir (özgün sistemdeki gibi). Hesap başına başarısızlık sınırı (dakikada 5) ve hesap kilitleme bu değerden bağımsız olarak uygulanır.

## Ortam değişkenleri

`.env.example` geliştirme varsayılanlarını içerir. Üretimde gizli bilgileri gizli bilgi deposundan aktarın.

| Değişken | Üretim değeri | Notlar |
|---|---|---|
| `DJANGO_ENV` | `production` | `setup_demo` komutunu reddeder ve ortam etiketini yönetim panelinden kaldırır |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, güvenli çerezler |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | Gizli bilgi deposu | [Anahtar yönetimi](security-keys.md). Yenilerken önceki anahtarlar `DJANGO_SECRET_KEY_FALLBACKS` değişkenine gider |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | Virgülle ayrılmış listeler |
| `APP_URL` | `https://sis.example.ac.kr` | E-postalardaki bağlantılar, belge doğrulama QR kodları |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | Gizli bilgi deposu | Kaybolursa kişisel verilerin şifresi çözülemez |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | Uygulama ve Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | `migrate`, `setup_install`, `audit_seal` ve `audit_prune` tarafından kullanılır. Parolayı yalnızca dağıtımları çalıştıran sunucuda ve denetim mühürlemesini (`audit_seal`) çalıştıran sunucuda tutun |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, [yük testi](load-testing.md) sonucundaki değer, `60`, `2000`, `127.0.0.1` | `config/gunicorn.py` tarafından okunur. Varsayılan worker sayısı CPU çekirdeği başına 2 + 1'dir. `GUNICORN_FORWARDED_ALLOW_IPS` yalnızca gunicorn'un kimin `X-Forwarded-Proto` başlığına güveneceğini belirtir; istemci adresi `TRUSTED_PROXY_COUNT` değerinden gelir |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | [Yük testinde](load-testing.md) belirlenen değerler: `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` hazırlanmış sorguları açar (RLS sorgu planlama maliyetini azaltır); 0 bunları kapatır |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | İç Redis | Aracı (broker) ve sonuçlar varsayılan olarak `REDIS_URL` kullanır |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | Üniversitenin SMTP aktarıcısı | Davetler, iki adımlı doğrulama kodları, ders kaydı ve not bildirimleri |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | İç adres, `60` | |
| `PRIVATE_MEDIA_ROOT` | Yedeklenen bir disk | Özel dosya deposu |
| `TRUSTED_PROXY_COUNT` | Genellikle `1` | Yukarıdaki bölüm |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` veya daha yüksek | Yukarıdaki bölüm |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | HTTPS'i ilk kez etkinleştirirken artırmadan önce kısa bir HSTS (`300`) deneyin |
| `SESSION_LIFETIME_MINUTES` | `120` | Oturum açılmış bir oturumun ömrü |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, kurumun saat dilimi | Sunucu zamanları ve zamanlanmış işler UTC'de, ekranlar kurumun saat diliminde |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | Varsayılanlar | [LMS entegrasyon kılavuzu](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | Günlükler standart çıktıya satır başına bir JSON nesnesi olarak gider |
| `VITE_DEV_MODE` | `false` | Üretim derleme çıktısını (`static/dist/manifest.json`) kullanır |

## Dağıtım prosedürü

1. Yedek alın ([yedekleme ve geri yükleme](backup-restore.md)) ve `uv run manage.py audit_verify_chain` çalıştırın.
2. Kodu dağıtın: `git pull` (veya yeni bir imaj), `uv sync --frozen --no-dev`, `npm ci && npm run build`.
3. `uv run manage.py setup_install --force`: migration'lar (otomatik olarak `app_migrator` bağlantısına geçer), yenilenen temel veriler (yönetici düzenlemeleri korunur), yetki kataloğu eşitlemesi. Migration'ları tek başına çalıştırırken `uv run manage.py migrate` de otomatik olarak `app_migrator` kullanır. DDL'i `app_runtime` olarak çalıştırmanın bir yolu yoktur.
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`. Üretim Docker imajı ikisini de derleme sırasında çalıştırır.
5. Süreçleri yeniden başlatın: gunicorn `reload` (HUP), Celery worker (TERM çalışan görevlerin bitmesine izin verir; `acks_late` ile yarıda kalan bir görev yeniden çalışır), Celery beat. Tüm sunucularda **tam olarak bir beat süreci** çalıştırın. İki tane olursa her zamanlanmış iş iki kez kuyruğa alınır (her işin Redis kilidi eşzamanlı çalışmayı engeller, çift kuyruğa almayı değil).
6. Doğrulayın: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (çıkış kodu 0), `GET /api/v1/health/` (`ok`), yönetim paneline oturum açma, `uv run manage.py pdf_sample`. Flower içinde worker'ın bağlı olduğunu kontrol edin.

## Rutin kontroller

| Sıklık | Görev |
|---|---|
| Günlük (otomatik) | `audit.seal`, `lms.reconcile`, ders kaydındaki ayrılmış kontenjanların serbest bırakılması, bekleme listesinden kayda alma, başvuru taslaklarının süresinin dolması ([zamanlanmış işler](scheduled-jobs.md)) |
| Haftalık | `/api/v1/health/` ve `check --deploy`, Python, işletim sistemi ve bağımlılık güvenlik güncellemeleri (`pip-audit`), Flower'daki başarısız görevler |
| Aylık | `media_prune_orphans --dry-run`, yedekten geri yükleme tatbikatı, `audit_verify_chain` |
| Her dönem | Rol atamalarının gözden geçirilmesi (ayrılan veya görev yeri değişen kişiler), saklama süresi geçmiş denetim kayıtlarının temizlenmesi (`audit_prune`), ders kaydından önce `LOGIN_RATE_LIMIT_PER_IP` ve worker sayısının yeniden kontrolü |
