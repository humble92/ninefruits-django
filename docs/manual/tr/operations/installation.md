# Kurulum

- Hedef kitle: BT operatörleri
- İlgili: [komut başvurusu](commands.md), [anahtar yönetimi](security-keys.md), [dağıtım kontrol listesi](deployment-checklist.md)

## 1. Gereksinimler

| Bileşen | Sürüm | Notlar |
|---|---|---|
| Python | 3.14 | [uv](https://docs.astral.sh/uv/) ile kurulur ve çalıştırılır (`uv sync`). Sistem paketleri: `gettext` (çevirilerin derlenmesi), `libmagic` (dosya türü algılama) |
| Node.js | 22 | Ekran varlıklarını derler (`npm ci && npm run build`). Üretim sunucularının yalnızca derleme çıktısına ihtiyacı vardır |
| PostgreSQL | 18 | `btree_gist` ve `pg_trgm` eklentileri (migration'lar tarafından kurulur), ICU harmanlaması |
| Redis | 8 | Önbellek, oturumlar, Celery aracısı (broker) ve sonuçları |
| Gotenberg | 8 | PDF üretimi. Yalnızca iç ağda erişilebilir |
| E-posta sunucusu | SMTP | Parola sıfırlama, iki adımlı doğrulama e-posta kodları, davetler, bildirimler |
| Web sunucusu | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`. Nginx `staticfiles/` dizinini kendisi sunar ve geri kalan her şeyi gunicorn'a iletir |
| Kuyruk çalışanı | Celery worker | `uv run celery -A config worker` komutunu bir süreç yöneticisi (systemd, supervisor) altında sürekli çalışır tutun |
| Zamanlayıcı | Celery beat | `uv run celery -A config beat` komutunu **tam olarak bir** makinede çalıştırın (veritabanı zamanlayıcısı, django-celery-beat) |
| Kuyruk izleme | Flower (isteğe bağlı) | `uv run celery -A config flower`. İç ağda veya bir Nginx erişim kısıtlamasının (ya da Flower'ın `--basic-auth` seçeneğinin) arkasında tutun; asla dışarıya açmayın |

## 2. Veritabanı hazırlığı

Veritabanı süper kullanıcısı olarak bir kez çalıştırın. Uygulama hiçbir zaman süper kullanıcıyı kullanmaz.

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| Rol | Ortam değişkenleri | Amaç |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | Uygulamanın çalışması (satır düzeyi güvenlik uygulanır, DDL yok) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | Yalnızca migration'lar, denetim mühürleme ve temizleme (`migrate` bu bağlantıyı otomatik olarak kullanır) |
| `app_reporting` | (BI araçlarında yapılandırılır) | `reporting` şemasının okunması |

Docker Compose geliştirme ortamında `docker/pgsql/20-create-app-roles.sh`, `pgsql` konteyneri ilk kez başladığında aynı işi yapar (roller, `ninefruits` ve test veritabanları).

## 3. Ortam yapılandırması

`.env.example` dosyasını `.env` olarak kopyalayın ve değerleri doldurun (üretimde bunları ortam değişkenleri olarak veya bir gizli bilgi deposundan sağlayın). Değiştirilmesi gereken değerler:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`. [Anahtar yönetimi](security-keys.md) belgesinde anlatıldığı gibi saklayın.
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`. **Kaybolurlarsa şifrelenmiş kişisel veriler kurtarılamaz.** [Anahtar yönetimi](security-keys.md) belgesinde anlatıldığı gibi ayrı olarak saklayın.
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: uygulamanın önündeki ters proxy sayısı (tek bir Nginx için `1`). Bkz. [dağıtım kontrol listesi](deployment-checklist.md#proxyler-ve-istemci-adresi)
- `INSTITUTION_TIMEZONE`: ilk kurulumdaki varsayılan kurum saat dilimi (örneğin `Asia/Seoul`)

Üretim ortam değişkenlerinin tam listesi [dağıtım kontrol listesindedir](deployment-checklist.md#ortam-değişkenleri).

## 4. Kurulum

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` sırasıyla şunları çalıştırır: migration'lar (`app_migrator` bağlantısı üzerinden), temel veriler (rol şablonları ve yetki eşitlemesi, ülkeler, diller, kod listesi türleri, birim türleri, durum değişikliği türleri, ders kaydı kural paketleri), kurum varsayılanları (varsayılan dil, saat dilimi, kurum adı), not ölçeğinin sabitlenmesi, kurulum profilleri ve ilk yönetici. Dağıtım betiklerinde `--force` ve seçeneklerle çalıştırın; yönetici parolası standart girdiden okunur.

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

Kurulum profilleri (`--profile=`, birden fazla kez verilebilir)

| Anahtar | İçerik |
|---|---|
| `korean-university` | İlkbahar/yaz/güz/kış dönem türleri, 4.5 not ölçeği, ders türleri, 09:00'da başlayan ders saatleri, derslik türleri, kabul türleri ve başvuru evrakları, varsayılan ders değerlendirme formu, dört dilde şablonlarıyla belge türleri |
| `yust-legacy` | `korean-university` içindeki her şey, ayrıca giriş yılına göre ve hemşirelik için kredi sınırları, sınır dışındaki kredi bankası dersleri, 4.3 not ölçeği ve notlandırma politikası |

Profil olmadan bunları yönetim panelinde girin. Bir profil daha sonra yeniden uygulandığında yöneticilerin değiştirdiği değerler korunur. Not ölçeği bir kez ayarlandıktan sonra değiştirilemez (notlar ve not ortalamaları bu ölçekte saklanır).

Django'nun `createsuperuser` komutu devre dışıdır. İlk yönetici yalnızca `setup_install` veya `security_create_administrator` ile oluşturulur ([komut başvurusu](commands.md)).

Kurulumdan sonra iş yöneticileri, temel verileri [yönetici kılavuzu 5. bölüm, ilk ayar sırası](../admin/05-institution-setup.md) belgesini izleyerek girer. Sunucu süreçlerini (gunicorn, Celery worker, beat) [dağıtım kontrol listesi](deployment-checklist.md) ve [zamanlanmış işler](scheduled-jobs.md) belgelerinde anlatıldığı gibi kaydedin.

### Docker Compose (geliştirme)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| Hizmet | Adres |
|---|---|
| Uygulama | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (geliştirme posta kutusu) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite geliştirme sunucusu (isteğe bağlı, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

Üretim imajı `Dockerfile` dosyasının `production` hedefidir (varsayılan). Derleme sırasında `compilemessages` ve `collectstatic` çalıştırır ve gunicorn'u başlatır. Aynı imaj worker'ı ve beat'i de çalıştırır (`uv run --no-sync celery -A config worker|beat`).

## 5. Kurulumun doğrulanması

1. `/accounts/login/` adresinde ilk yönetici olarak oturum açın. `/admin/` açılır ve kenar çubuğunda **Kullanıcılar ve erişim**, **Denetim** ve **Ayarlar** görünür.
2. Yönetim panelinde **Ayarlar > Güvenlik** altında iki adımlı doğrulama politikasını belirleyin.
3. Yönetici için iki adımlı doğrulamayı kurun (portal **Güvenlik**, `/portal/security/`).
4. PDF hizmetini `uv run manage.py pdf_sample` ile kontrol edin.
5. Yönetim panelinde **Denetim > Veri değişiklikleri** altında kurulumun `system:command:setup_install` olarak göründüğünü kontrol edin.
6. `uv run manage.py check --deploy` komutunun üretim uyarısı vermediğini ve `GET /api/v1/health/` isteğinin `{"status": "ok"}` yanıtı verdiğini kontrol edin (beat'in bir dakika çalışmış olması gerekir).

## 6. Güncelleme

```bash
git pull
uv sync --frozen --no-dev
npm ci && npm run build
uv run manage.py setup_install --force      # migrations, essential data, permission sync
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
sudo systemctl reload ninefruits-gunicorn          # restart the web workers on the new code
sudo systemctl restart ninefruits-celery ninefruits-beat
```

Hizmet adlarını kendi kurulumunuza göre uyarlayın. Bir güncellemenin öncesindeki ve sonrasındaki yedekleme ve kontroller için [dağıtım kontrol listesini](deployment-checklist.md#dağıtım-prosedürü) izleyin.
