# डिप्लोय जाँचसूची र gunicorn तथा Python सेटिङ

- लक्षित पाठक: IT सञ्चालकहरू
- सम्बन्धित: [स्थापना](installation.md), [कुञ्जी व्यवस्थापन](security-keys.md), [निर्धारित कार्यहरू](scheduled-jobs.md), [लोड परीक्षण](load-testing.md)

## Python र निर्भरताहरू

- **Python 3.14** को पछिल्लो patch रिलिज प्रयोग गर्नुहोस्। कन्टेनर वा सर्भर इमेज बिल्ड गर्दा Python को patch संस्करण स्थिर नगर्नुहोस्; पछिल्लो लिनुहोस् (`Dockerfile` मा `python:3.14-slim`)।
- Python निर्भरताहरू `uv.lock` मा लक गरिएका छन्। उत्पादन स्थापनाले सधैँ `uv sync --frozen --no-dev` प्रयोग गर्छ (lock फाइल नमिलेमा असफल हुन्छ)। विकास उपकरणहरू (pytest, ruff, mypy, Playwright) कहिल्यै उत्पादनमा पुग्दैनन्।
- Django ले सुरक्षा रिलिज प्रकाशित गर्दा `uv lock --upgrade-package django` बाट अपग्रेड गर्नुहोस्, परीक्षण चलाउनुहोस् र डिप्लोय गर्नुहोस्। निर्भरताका कमजोरीहरू CI ले जस्तै जाँच्नुहोस्: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`।
- `uv run manage.py check --deploy` ले उत्पादन सेटिङ (`DEBUG`, HTTPS, cookie, HSTS, गोप्य कुञ्जीको लम्बाइ) बारे चेतावनी दिन्छ। हरेक डिप्लोयमा शून्य चेतावनी हुनुपर्छ।

## gunicorn र Nginx

| वस्तु | मान | कारण |
|---|---|---|
| gunicorn चलाउने | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, sync worker। worker सङ्ख्या र जडान pool को आकार वातावरण चरबाट आउँछन्; तर्क [लोड परीक्षण](load-testing.md) मा छ |
| gunicorn bind | `127.0.0.1:8000` वा Unix socket | gunicorn लाई कहिल्यै सिधै खुला नगर्नुहोस्; सधैँ Nginx पछाडि राख्नुहोस् |
| worker पुनः सुरु | डिप्लोयमा `HUP` (systemd `reload`) | चलिरहेका अनुरोध पूरा गरेर worker लाई नयाँ कोडले प्रतिस्थापन गर्छ |
| DB जडान | `DB_POOL=true` हुँदा प्रति worker psycopg जडान pool (`DB_POOL_MIN`, `DB_POOL_MAX`) | worker × `DB_POOL_MAX` + Celery जडान PostgreSQL को `max_connections` भन्दा कम रहनुपर्छ। pool मा फर्काइएको जडानको DB सत्र कर्ता खाली गरिन्छ (`ninefruits.core.pool.reset_connection`) |
| Nginx `client_max_body_size` | `32m` | भर्ना कागजात, परीक्षाका प्रमाण र फोटो अपलोडको माथिल्लो सीमा (एप्लिकेसनको 5MB र 2MB प्रमाणीकरणभन्दा बढी ठाउँ) |
| Nginx स्थिर फाइल | `location /static/ { alias <repository>/staticfiles/; }` | Nginx ले `collectstatic` को आउटपुट आफैँ सेवा गर्छ |
| निजी फाइल | Nginx मा `PRIVATE_MEDIA_ROOT` (पूर्वनिर्धारित `storage/private`) **कहिल्यै map नगर्नुहोस्** | फोटो, आवेदनका कागजात र प्रमाणपत्र PDF अनुमति जाँच गर्ने view बाट मात्र डाउनलोड हुन्छन् |
| Nginx हेडर | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host`, वैकल्पिक रूपमा `X-Request-Id $request_id` | क्लाइन्टको ठेगाना, HTTPS पहिचान, प्रति-अनुरोध ट्रेसिङ |
| Gotenberg, Redis, PostgreSQL | आन्तरिक ठेगाना मात्र | कहिल्यै बाहिर खुला नगरिने |

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

### प्रोक्सी र क्लाइन्टको ठेगाना

साइन इन सीमा, API दर सीमा र अडिट अभिलेखका IP ठेगानाहरूले `ninefruits.core.http.client_ip` ले निर्धारण गरेको क्लाइन्ट ठेगाना प्रयोग गर्छन्।

- `TRUSTED_PROXY_COUNT`: एप्लिकेसनअगाडि `X-Forwarded-For` मा थप्ने रिभर्स प्रोक्सीहरूको सङ्ख्या। एउटा Nginx का लागि `1`, लोड ब्यालेन्सर र Nginx का लागि `2`। `0` (पूर्वनिर्धारित) ले `REMOTE_ADDR` प्रयोग गर्छ। दायाँबाट यति स्थान परको प्रविष्टि क्लाइन्टको ठेगाना हो; त्योभन्दा बायाँका प्रविष्टिहरू (क्लाइन्टले पठाएका) कहिल्यै विश्वास गरिँदैनन्।
- **मान वास्तविक प्रोक्सी सङ्ख्याभन्दा कम भएमा** सबै प्रयोगकर्ता Nginx को ठेगानाबाट आएजस्तो देखिन्छन् र साइन इन सीमा एकैपटक पूरै क्याम्पसमा लागू हुन्छ। **बढी भएमा** एप्लिकेसनले क्लाइन्टले पठाएको `X-Forwarded-For` विश्वास गर्छ, र सीमाहरू छल्न सकिन्छ। डिप्लोयपछि प्रशासन प्यानलको **अडिट > सुरक्षा घटनाहरू** का IP ठेगाना वास्तविक प्रयोगकर्ताका ठेगाना हुन् कि भनी जाँच्नुहोस्।
- `LOGIN_RATE_LIMIT_PER_IP`: प्रति क्लाइन्ट ठेगाना साइन इन प्रयास (django-allauth, पूर्वनिर्धारित `30/m/ip`)। मूल प्रणालीमा यस्तो सीमा थिएन। पूरै क्याम्पस एउटै NAT ठेगानाबाट बाहिर जान्छ भने विषय दर्ताको पहिलो बिहानका लागि यो धेरै कम हुन्छ; बढाउनुहोस् (उदाहरणका लागि `300/m/ip`)। खाली भनेको प्रति ठेगाना सीमा छैन (मूल प्रणालीजस्तै)। प्रति खाता असफलताको सीमा (प्रति मिनेट 5) र खाता लक यो मान जेसुकै भए पनि लागू हुन्छन्।

## वातावरण चरहरू

`.env.example` मा विकासका पूर्वनिर्धारित मानहरू छन्। उत्पादनमा गोप्य मानहरू गोप्य भण्डारबाट दिनुहोस्।

| चर | उत्पादनको मान | टिप्पणी |
|---|---|---|
| `DJANGO_ENV` | `production` | `setup_demo` अस्वीकार गर्छ र प्रशासन प्यानलबाट वातावरण ब्याज हटाउँछ |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS, सुरक्षित cookie |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | गोप्य भण्डार | [कुञ्जी व्यवस्थापन](security-keys.md)। परिवर्तन गर्दा अघिल्ला कुञ्जीहरू `DJANGO_SECRET_KEY_FALLBACKS` मा जान्छन् |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | अल्पविरामले छुट्याइएका सूची |
| `APP_URL` | `https://sis.example.ac.kr` | मेलका लिङ्क, प्रमाणपत्र प्रमाणीकरणका QR कोड |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | गोप्य भण्डार | हराएमा व्यक्तिगत डेटा डिक्रिप्ट गर्न सकिँदैन |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | एप्लिकेसन र Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | `migrate`, `setup_install`, `audit_seal` र `audit_prune` ले प्रयोग गर्छन्। पासवर्ड डिप्लोय चलाउने सर्भर र अडिट सिल (`audit_seal`) चलाउने सर्भरमा मात्र राख्नुहोस् |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000`, [लोड परीक्षण](load-testing.md) को मान, `60`, `2000`, `127.0.0.1` | `config/gunicorn.py` ले पढ्छ। पूर्वनिर्धारित worker सङ्ख्या प्रति CPU core 2 + 1 हो। `GUNICORN_FORWARDED_ALLOW_IPS` ले gunicorn ले कसको `X-Forwarded-Proto` विश्वास गर्छ भन्ने मात्र बताउँछ; क्लाइन्टको ठेगाना `TRUSTED_PROXY_COUNT` बाट आउँछ |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | [लोड परीक्षण](load-testing.md) मा तय गरिएका मान: `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` ले prepared statement सक्रिय गर्छ (RLS query योजनाको लागत घटाउँछ); 0 ले बन्द गर्छ |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | आन्तरिक Redis | broker र नतिजा पूर्वनिर्धारित रूपमा `REDIS_URL` |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | विश्वविद्यालयको SMTP relay | निमन्त्रणा, दुई-चरण कोड, विषय दर्ता र ग्रेडका सूचना |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | आन्तरिक ठेगाना, `60` | |
| `PRIVATE_MEDIA_ROOT` | ब्याकअप हुने डिस्क | निजी फाइल भण्डारण |
| `TRUSTED_PROXY_COUNT` | सामान्यतया `1` | माथिको खण्ड |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` वा बढी | माथिको खण्ड |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | पहिलो पटक HTTPS सक्षम गर्दा बढाउनुअघि छोटो HSTS (`300`) प्रयास गर्नुहोस् |
| `SESSION_LIFETIME_MINUTES` | `120` | साइन इन भएको सत्रको आयु |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC`, संस्थाको समय क्षेत्र | सर्भरका समय र निर्धारित कार्य UTC मा, स्क्रिनहरू संस्थाको समय क्षेत्रमा |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | पूर्वनिर्धारित | [LMS एकीकरण गाइड](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | लगहरू standard output मा प्रति पङ्क्ति एउटा JSON वस्तुका रूपमा जान्छन् |
| `VITE_DEV_MODE` | `false` | उत्पादनले बिल्ड आउटपुट (`static/dist/manifest.json`) प्रयोग गर्छ |

## डिप्लोय प्रक्रिया

1. ब्याकअप लिनुहोस् ([ब्याकअप र पुनर्स्थापना](backup-restore.md)) र `uv run manage.py audit_verify_chain` चलाउनुहोस्।
2. कोड डिप्लोय गर्नुहोस्: `git pull` (वा नयाँ इमेज), `uv sync --frozen --no-dev`, `npm ci && npm run build`।
3. `uv run manage.py setup_install --force`: migration (स्वतः `app_migrator` जडानमा सरेर), आवश्यक डेटा ताजा (प्रशासकका सम्पादन कायम रहन्छन्), अनुमति क्याटलग सिङ्क। migration मात्र छुट्टै चलाउँदा `uv run manage.py migrate` ले पनि स्वतः `app_migrator` प्रयोग गर्छ। `app_runtime` का रूपमा DDL चलाउने कुनै उपाय छैन।
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput`। उत्पादनको Docker इमेजले दुवै बिल्डका बेला चलाउँछ।
5. प्रक्रियाहरू पुनः सुरु गर्नुहोस्: gunicorn `reload` (HUP), Celery worker (TERM ले चलिरहेका कार्य पूरा हुन दिन्छ; `acks_late` सहित, बीचमा रोकिएको कार्य फेरि चल्छ), Celery beat। सबै सर्भरमा मिलाएर **ठ्याक्कै एउटा beat प्रक्रिया** चलाउनुहोस्। दुईवटा भएमा हरेक निर्धारित कार्य दुई पटक क्युमा राखिन्छ (प्रत्येक कार्यको Redis lock ले एकैसाथ चल्न रोक्छ, दोहोरो क्युमा राख्न होइन)।
6. प्रमाणित गर्नुहोस्: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (निकास कोड 0), `GET /api/v1/health/` (`ok`), प्रशासन प्यानलमा साइन इन, `uv run manage.py pdf_sample`। worker जोडिएको छ कि भनी Flower मा जाँच्नुहोस्।

## नियमित जाँच

| आवृत्ति | काम |
|---|---|
| दैनिक (स्वचालित) | `audit.seal`, `lms.reconcile`, आरक्षित दर्ता सिट खुला गर्ने, प्रतीक्षा सूचीबाट दर्ता, आवेदन मस्यौदाको म्याद ([निर्धारित कार्यहरू](scheduled-jobs.md)) |
| साप्ताहिक | `/api/v1/health/` र `check --deploy`, Python, OS र निर्भरताका सुरक्षा अद्यावधिक (`pip-audit`), Flower मा असफल कार्यहरू |
| मासिक | `media_prune_orphans --dry-run`, ब्याकअप पुनर्स्थापना अभ्यास, `audit_verify_chain` |
| हरेक सेमेस्टर | भूमिका तोकाइ समीक्षा (छाडेका वा सरुवा भएका व्यक्ति), अवधारण अवधि नाघेका अडिट अभिलेख छँटाइ (`audit_prune`), विषय दर्ताअघि `LOGIN_RATE_LIMIT_PER_IP` र worker सङ्ख्या फेरि जाँच |
