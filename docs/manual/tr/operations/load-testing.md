# Yük testi (ders kaydı yoğunluğu)

- Hedef kitle: BT operatörleri
- İlgili: [dağıtım kontrol listesi](deployment-checklist.md), [kurulum](installation.md), [komutlar](commands.md)

Locust, çok sayıda öğrencinin aynı anda aynı şubelere yüklendiği ders kaydının ilk sabahını yeniden üretir. Betik `loadtest/registration.py` (özgün sistemin k6 `tests/load/registration.js` betiği), çalıştırma yardımcısı `loadtest/run.sh`, kontenjan aşımı kontrolü ise `loadtest/seat_check.sql` dosyasıdır.

[Kılavuz içindekiler](../README.md)

## Hazırlık

1. Yalnızca yük testi için bir veritabanı oluşturun (asla üretim veritabanını kullanmayın). Roller ve veritabanı [kurulum](installation.md) belgesinin 2. bölümündeki gibi oluşturulur; ardından kurulumu yapın ve büyük demoyu yükleyin. Öğrenci hesap listesi özel depolamadaki `load-accounts.csv` dosyasına yazılır (`PRIVATE_MEDIA_ROOT`, varsayılan `storage/private`).

   ```bash
   export DB_DATABASE=nf_load
   uv run manage.py setup_install --profile=korean-university --grade-scale=4.5 --force < /dev/null
   uv run manage.py setup_demo --size=large --seed=42 --student-accounts --force
   ```

2. Bir ders kaydı aralığının açık olması gerekir. Demo, bir sonraki dönemin ders kaydı aralıklarını sınıfa göre oluşturur (4. sınıf zaten açık, 3. sınıf iki gün sonra, 1. ve 2. sınıflar üç gün sonra). Her sınıfla ölçüm yapmak için diğer ders kaydı aralıklarının başlangıcını dönemin **Düzenle** sayfasındaki **İşlem aralıkları** altında geçmişe alın ([yönetici kılavuzu, bölüm 10](../admin/10-terms.md)) veya test veritabanında süper kullanıcı olarak şunu çalıştırın:

   ```sql
   UPDATE term_windows SET opens_at = now() - interval '1 hour'
    WHERE window_type = 'registration' AND opens_at > now() AND closes_at > now();
   ```

3. Redis ve bir Celery worker çalışıyor olmalıdır. Kontenjanlara doğrudan veritabanında karar verilir, ancak bekleme listesinden kayda alma, LMS eşitlemesi ve bildirimler kuyruktan geçer. Redis başka işlerle paylaşılıyorsa başka bir veritabanı numarası kullanın, örn. `REDIS_URL=redis://127.0.0.1:6379/7`.

## Çalıştırma

`loadtest/run.sh` gunicorn'u (`config/gunicorn.py`) ve bir Celery worker'ı başlatır, Locust'u arayüzsüz (headless) çalıştırır, kontenjan kontrolünü yapar ve her şeyi durdurur.

```bash
export DB_DATABASE=nf_load DB_POOL=true DB_POOL_MIN=1 DB_POOL_MAX=2 DB_PREPARE_THRESHOLD=2
WORKERS=9 USERS=100 DURATION=1m loadtest/run.sh storage/loadtest/w9-u100
```

Elle çalıştırmak için sunucuyu `TRUSTED_PROXY_COUNT=1` ile başlatın ve Locust'u çalıştırın:

```bash
TRUSTED_PROXY_COUNT=1 DJANGO_DEBUG=false GUNICORN_WORKERS=9 uv run gunicorn config.wsgi -c config/gunicorn.py
uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \
    --host http://127.0.0.1:8000 --csv storage/loadtest/run
psql -h 127.0.0.1 -U postgres -d nf_load -v term=<term id> -f loadtest/seat_check.sql
```

- Senaryo: oturum açma (`/accounts/login/`) → ders kaydı sayfası → ders arama (HTMX `?partial=results`) → boş kontenjanı olan ilk şubeye kayıt → dersi bırakma. Her yineleme çerezleri temizler ve bir sonraki öğrenci olarak oturum açar. Dolu şubeler ve kural retleri normal sonuçlar olarak sayılır (`registration outcomes`).
- Kayıt ve bırakma düğmeleri HTMX gibi gönderir (`HX-Request`); sunucu ders kaydı sayfasına 302 ile yanıt verir. `enroll` ve `drop` süreleri bu sayfayı içerir (tarayıcının `#registration` öğesini değiştirmeden önce ona ihtiyacı vardır).
- Her öğrenci kendi `X-Forwarded-For` adresini gönderir. Sunucu tek bir proxy katmanının arkasındayken (`TRUSTED_PROXY_COUNT=1`) allauth'un adres başına oturum açma sınırı, gerçek bir kampüsteki gibi öğrenci adresi başına uygulanır. `ADDRESSES=1` tüm öğrencileri tek bir adresin (NAT) arkasında yeniden üretir.
- Ortam: `ACCOUNTS` (hesap CSV'si), `SEARCH` (arama metni, varsayılan `GEN`), `ADDRESSES`, `FIRST_ACCOUNT` (ilk hesap, varsayılan olarak rastgele). `run.sh` şunları alır: `WORKERS`, `USERS`, `SPAWN_RATE`, `DURATION`, `TERM_ID`, `PORT`.
- `USERS` değerini 100'den 200'e ve 500'e çıkarın ve her sayfanın p95 değerini ve hata oranını izleyin. Eşikler: ders kaydı sayfası p95 < 800 ms, kayıt p95 < 1,5 s, hatalar < %1. Bir eşik karşılanmadığında Locust 1 koduyla çıkar.
- Sunucuda `pg_stat_activity` içindeki bağlantı sayısını ve kilit beklemelerini (`wait_event_type = 'Lock'`), Celery birikimini ve CPU doygunluğunu izleyin. Aynı sunucudaki Locust da CPU kullanır; bu nedenle sayılar bir alt sınırdır.

## Tasarımın garanti ettikleri

- Kontenjan, şube satırı kilidi (`SeatAllocator.lock`, `SELECT ... FOR NO KEY UPDATE`) ve CHECK kısıtlarıyla korunur; bu nedenle eşzamanlı istekler bir şubede kontenjanı asla aşmaz (`tests/registration/test_concurrent_registration.py`: 16 süreç, 5 kontenjan). Kilit yalnızca aynı şubenin kontenjanı için gelen istekleri birbirini beklemeye zorlar; şubeye yalnızca başvuran satırların (ders kaydı denemeleri, LMS eşitleme günlükleri) yabancı anahtar kontrollerini engellemez.
- Bir çalıştırmadan sonra `loadtest/seat_check.sql` dosyasındaki dört sorgu hiçbir satır döndürmemelidir (kontenjan aşımı, kontenjan sayacı uyuşmazlığı, kontenjan grubu aşımı, bir şubede mükerrer ders kaydı).
- Ders kaydı sayfasının sorgu sayısı ders kayıtları, bekleme listesi kayıtları veya arama sonuçlarıyla artmaz (`tests/registration/test_portal_query_count.py`).

## Adres başına oturum açma sınırı ve proxy'ler

Hesap başına başarısızlık sınırının (dakikada 5) yanı sıra allauth, özgün sistemde olmayan bir **adres başına oturum açma sınırı** (`LOGIN_RATE_LIMIT_PER_IP`, varsayılan `30/m/ip`) uygular. Uygulamanın gördüğü adres `TRUSTED_PROXY_COUNT` ile belirlenir (`ninefruits.core.http.client_ip`).

- Nginx'in arkasında `TRUSTED_PROXY_COUNT=0` (varsayılan) ile her istek Nginx adresine sahiptir. Tek bir NAT adresinden çıkan bir kampüs de aynı durumdadır.
- Bunu yeniden üreten bir çalıştırmada (`ADDRESSES=1`, 100 VU, 1 dakika): 4.876 oturum açmadan **yalnızca 30'u başarılı oldu** ve 4.846'sı 429 ile reddedildi (%49 hata). O dakikada yalnızca 20 ders kaydı gerçekleşti. Aynı koşullarda öğrenci başına bir adresle hiçbir oturum açma reddedilmedi.
- Üretim ayarları: `TRUSTED_PROXY_COUNT` değerini proxy sayısına ayarlayın (tek bir Nginx için `1`). Öğrencilerin çoğu tek bir NAT adresini paylaşıyorsa `LOGIN_RATE_LIMIT_PER_IP` değerini en yoğun oturum açma hızına çıkarın. Örnek: 10 dakika içinde oturum açan 2.000 öğrenci, tek bir adresten dakikada 200 demektir; bu nedenle `300/m/ip`. Boş bir değer adres başına sınırı kaldırır (özgün sistemdeki gibi; hesap başına başarısızlık sınırı kalır).

## Sunucu yapılandırma kararları

- **gunicorn sync worker'ları** (`config/gunicorn.py`). `GUNICORN_WORKERS` varsayılan olarak CPU çekirdeği × 2 + 1'dir. Verim CPU'ya bağlıydı: 4 çekirdekte 4, 9 ve 16 worker aynı verimi verdi (saniyede 23 ila 26 istek). Daha fazla worker yalnızca veritabanı bağlantılarını (12 → 36) ve kilit beklemelerini (tepe 1 → 12) artırdı. Çekirdek × 2 + 1'in üzerine çıkmayın; daha fazla uygulama sunucusuyla yatay ölçeklendirin.
- **Bağlantı havuzu ve hazırlanmış sorgular**: `DB_POOL=true`, `DB_POOL_MIN=1`, `DB_POOL_MAX=2`, `DB_PREPARE_THRESHOLD=2`. Satır düzeyi güvenlik (RLS) politikaları nedeniyle sorgu planlama, bir sayfanın veritabanı süresinin çoğunu oluşturuyordu (ders kaydı sayfasının 31 sorgusu: 51 ms planlama, 19 ms yürütme). Bağlantıları yeniden kullanmak ve sunucu tarafı bağlama ile sorguları hazırlamak her sorguyu bağlantı başına bir kez planlar. Aynı 4 çekirdekte verim saniyede 16,8'den 25,6 isteğe çıktı; tek kullanıcı için ders kaydı sayfasının ortancası 160 ms'den 97 ms'ye indi. Bir sunucunun, PostgreSQL'in `max_connections` değerinin altında kalan worker sayısı × `DB_POOL_MAX` + Celery eşzamanlılığı kadar bağlantıya ihtiyacı vardır. İşlem (transaction) kipindeki PgBouncer'ın arkasında hazırlanmış sorgular kullanılamaz: `DB_PREPARE_THRESHOLD=0` tutun. Tam test takımı (1.066 test) bu ayarlarla geçer.
- **ASGI (özgün sistemin Octane kararı)**: benimsenmedi. Her sayfa eşzamanlı bir görünümdür; ASGI bunları fayda sağlamadan bir iş parçacığında çalıştırırdı ve verim CPU çekirdeklerini izler. Django uygulamayı her istek için yeniden başlatmaz (PHP-FPM'in aksine); bu nedenle Octane'in sağladığı kazanç zaten vardır; kalıcı bağlantıların kazancı ise yukarıdaki havuzdan ve hazırlanmış sorgulardan gelir.
- Oturum açma, Argon2 karma kontrolü nedeniyle istek başına çok CPU harcar (tek kullanıcıyla yaklaşık 140 ms). Yoğunlukta oturum açmalar biriktiğinde bu maliyet önce verimi tüketir.

## 2026-10-24 tarihli ölçümler

Ortam: 4 vCPU (Xeon 2,1 GHz, `nproc` = 4), 15 GB RAM, başka işlerle paylaşılan bir geliştirme makinesi (test çalıştırmaları; ölçümler sırasında yük ortalaması 7 ila 21), Locust, gunicorn, PostgreSQL 18 ve Redis aynı makinede. Python 3.14, Django 6.1, gunicorn 26.2, `DJANGO_DEBUG=false`. Demo `--size=large --seed=42` (20.004 öğrenci, 11.437 öğrenci hesabı, 416 saniyede oluşturuldu), 2027 bahar dönemi ders kaydı aralığı her sınıf için açık, 52 yayımlanmış şube (2.262 kontenjan). Her biri bir dakika, `TRUSTED_PROXY_COUNT=1`, öğrenci başına bir adres.

| Koşul | Verim | Sayfa p95 | Kayıt p95 | Hatalar | Kaydedilen / reddedilen | En fazla PG bağlantısı |
|---|---|---|---|---|---|---|
| 2 VU, 9 worker, havuz yok | 5,1 istek/s | 200 ms | 640 ms | 0 / 300 | 50 / 0 | 3 |
| 2 VU, 9 worker, havuz + hazırlanmış sorgular | 6,2 istek/s | 160 ms | 470 ms | 0 / 372 | 62 / 0 | 22 |
| 100 VU, 4 worker, havuz yok | 16,8 istek/s | 6,0 s | 11 s | 0 / 1.005 | 52 / 86 | 6 |
| 100 VU, 16 worker, havuz yok | 17,1 istek/s | 6,1 s | 11 s | 0 / 1.027 | 60 / 86 | 18 |
| 100 VU, 4 worker, havuz + hazırlanmış sorgular | 25,6 istek/s | 4,1 s | 7,0 s | 0 / 1.536 | 97 / 155 | 12 |
| 100 VU, 9 worker, havuz + hazırlanmış sorgular | 25,4 istek/s | 4,5 s | 7,3 s | 0 / 1.523 | 77 / 167 | 22 |
| 100 VU, 16 worker, havuz + hazırlanmış sorgular | 23,4 istek/s | 4,6 s | 8,4 s | 0 / 1.405 | 131 / 79 | 36 |
| 200 VU, 9 worker, havuz + hazırlanmış sorgular | 29,8 istek/s | 9,4 s | 14 s | 0 / 1.792 | 66 / 172 | 22 |
| 200 VU, 16 worker, havuz + hazırlanmış sorgular | 29,2 istek/s | 9,1 s | 14 s | 0 / 1.761 | 53 / 174 | 36 |
| 100 VU, 9 worker, tek adres (NAT) | (çoğunlukla 429) | 2,0 s | 3,3 s | 4.846 / 9.862 | 20 / 10 | 22 |

Nasıl okunur

- Hiçbir çalıştırmada (tek adresli çalıştırma hariç) HTTP hatası ve kontenjan aşımı yok (`seat_check.sql` hiçbir satır döndürmedi). Retler dolu şubeler (`capacity`) ve mükerrer derslerdir (`duplicate_course`, önceki bir çalıştırmanın sonunda kesilen yinelemelerden kalan kayıtlar): normal davranış.
- 100 VU'daki birkaç saniyelik gecikmeler istek kuyruğudur. Tek kullanıcıyla sunucu sayfayı yaklaşık 100 ms'de, bir ders kaydını (POST artı dönen sayfa) yaklaşık 290 ms'de işler; 4 çekirdeği Locust, PostgreSQL ve diğer işlerle paylaşan bu makine saniyede 25 ila 30 istekte tıkanır. Bu makinede eşikler (sayfa p95 < 800 ms, kayıt p95 < 1,5 s) 100 VU'da karşılanmaz.
- Kilit beklemeleri yalnızca aynı şubenin kontenjan kilitlerinden geldi ve kısaydı (anlık tepe 1 ila 12, worker arttıkça daha fazla). Veritabanı bağlantıları worker sayısı × 2 veya altında kaldı.
- Ders kaydı yoğunluğunu "10 dakika içinde her biri 6 istek yapan 2.000 öğrenci" olarak almak saniyede 20 istek eder. Bu makine (havuz + hazırlanmış sorgular) 25 ila 30 yaptı; bu nedenle ayrılmış 8 çekirdekli bir uygulama sunucusunun payı vardır. Canlıya geçmeden önce: aynı betiği üretim gibi yapılandırılmış bir hazırlık ortamında (ayrılmış uygulama sunucusu, Nginx, ayrı veritabanı sunucusu, Locust başka bir makinede) 200 ve 500 VU ile çalıştırın ve eşikleri doğrulayın.
- Özgün sistem (Laravel, Sail geliştirme konteyneri, yerleşik sunucu) 100 VU'da 4 worker ile 24,7 istek/s, 16 worker ile 34,5 istek/s yaptı. Makineler farklı olduğundan sayılar doğrudan karşılaştırılamaz.
