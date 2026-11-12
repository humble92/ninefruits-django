# स्थापना

- लक्षित पाठक: IT सञ्चालकहरू
- सम्बन्धित: [कमान्ड सन्दर्भ](commands.md), [कुञ्जी व्यवस्थापन](security-keys.md), [डिप्लोय जाँचसूची](deployment-checklist.md)

## 1. आवश्यकताहरू

| कम्पोनेन्ट | संस्करण | टिप्पणी |
|---|---|---|
| Python | 3.14 | [uv](https://docs.astral.sh/uv/) बाट स्थापना र सञ्चालन गरिन्छ (`uv sync`)। प्रणाली प्याकेजहरू: `gettext` (अनुवाद कम्पाइल), `libmagic` (फाइलको प्रकार पहिचान) |
| Node.js | 22 | स्क्रिनका asset बिल्ड गर्छ (`npm ci && npm run build`)। उत्पादन सर्भरलाई बिल्ड आउटपुट मात्र चाहिन्छ |
| PostgreSQL | 18 | `btree_gist`, `pg_trgm` एक्सटेन्सन (migration ले स्थापना गर्छ), ICU collation |
| Redis | 8 | क्यास, सत्र, Celery broker र नतिजा |
| Gotenberg | 8 | PDF निर्माण। आन्तरिक नेटवर्कमा मात्र खुला राख्नुहोस् |
| मेल सर्भर | SMTP | पासवर्ड रिसेट, दुई-चरण इमेल कोड, निमन्त्रणा, सूचना |
| वेब सर्भर | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py`। Nginx ले `staticfiles/` आफैँ सेवा गर्छ र बाँकी सबै gunicorn लाई पठाउँछ |
| क्यु worker | Celery worker | `uv run celery -A config worker` लाई प्रक्रिया व्यवस्थापक (systemd, supervisor) अन्तर्गत चलिरहन दिनुहोस् |
| अनुसूचक | Celery beat | `uv run celery -A config beat` लाई **ठ्याक्कै एउटा** मेसिनमा चलाउनुहोस् (डेटाबेस अनुसूचक, django-celery-beat) |
| क्यु मनिटर | Flower (वैकल्पिक) | `uv run celery -A config flower`। आन्तरिक नेटवर्कमा वा Nginx पहुँच प्रतिबन्ध (वा Flower को `--basic-auth`) पछाडि राख्नुहोस्; कहिल्यै बाहिर खुला नगर्नुहोस् |

## 2. डेटाबेस तयारी

डेटाबेस superuser का रूपमा एक पटक चलाउनुहोस्। एप्लिकेसनले superuser कहिल्यै प्रयोग गर्दैन।

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| भूमिका | वातावरण चरहरू | प्रयोजन |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | एप्लिकेसन चलाउने (पङ्क्ति स्तरको सुरक्षा लागू, DDL छैन) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | migration, अडिट सिल र छँटाइ मात्र (`migrate` ले यो जडान स्वतः प्रयोग गर्छ) |
| `app_reporting` | (BI उपकरणमा सेट गरिन्छ) | `reporting` स्किमा पढ्ने |

Docker Compose विकास वातावरणमा `pgsql` कन्टेनर पहिलो पटक सुरु हुँदा `docker/pgsql/20-create-app-roles.sh` ले यही काम गर्छ (भूमिकाहरू, `ninefruits` र परीक्षण डेटाबेसहरू)।

## 3. वातावरण कन्फिगरेसन

`.env.example` लाई `.env` मा प्रतिलिपि गरेर मानहरू भर्नुहोस् (उत्पादनमा तिनलाई वातावरण चर वा गोप्य भण्डारबाट दिनुहोस्)। परिवर्तन गर्नैपर्ने मानहरू:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"`। [कुञ्जी व्यवस्थापन](security-keys.md) मा वर्णन गरिएअनुसार भण्डारण गर्नुहोस्।
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key`। **यी हराएमा इन्क्रिप्ट गरिएको व्यक्तिगत डेटा पुनःप्राप्त गर्न सकिँदैन।** [कुञ्जी व्यवस्थापन](security-keys.md) मा वर्णन गरिएअनुसार छुट्टै भण्डारण गर्नुहोस्।
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: एप्लिकेसनअगाडिका रिभर्स प्रोक्सीको सङ्ख्या (एउटा Nginx का लागि `1`)। [डिप्लोय जाँचसूची](deployment-checklist.md#प्रोक्सी-र-क्लाइन्टको-ठेगाना) हेर्नुहोस्
- `INSTITUTION_TIMEZONE`: पहिलो स्थापनाका लागि संस्थाको पूर्वनिर्धारित समय क्षेत्र (उदाहरणका लागि `Asia/Seoul`)

उत्पादनका वातावरण चरहरूको पूरा सूची [डिप्लोय जाँचसूची](deployment-checklist.md#वातावरण-चरहरू) मा छ।

## 4. स्थापना

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` ले क्रमैसँग चलाउँछ: migration (`app_migrator` जडानमा), आवश्यक डेटा (भूमिका टेम्प्लेट र अनुमति सिङ्क, देशहरू, भाषाहरू, कोड सूचीका प्रकारहरू, संगठन एकाइका प्रकारहरू, स्थिति परिवर्तनका प्रकारहरू, विषय दर्ता नियमका बन्डलहरू), संस्थाका पूर्वनिर्धारित (पूर्वनिर्धारित भाषा, समय क्षेत्र, संस्थाको नाम), ग्रेड स्केल स्थिर गर्ने, स्थापना प्रोफाइलहरू र पहिलो प्रशासक। डिप्लोय स्क्रिप्टहरूमा यसलाई `--force` र विकल्पहरूसहित चलाउनुहोस्; प्रशासकको पासवर्ड standard input बाट पढिन्छ।

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

स्थापना प्रोफाइलहरू (`--profile=`, एकभन्दा बढी पटक दिन सकिन्छ)

| कुञ्जी | विषयवस्तु |
|---|---|
| `korean-university` | वसन्त/ग्रीष्म/शरद/शीत सेमेस्टरका प्रकार, 4.5 ग्रेड स्केल, विषयका वर्ग, 09:00 देखिका पिरियड, कोठाका प्रकार, भर्नाका प्रकार र आवेदनका कागजात, पूर्वनिर्धारित विषय मूल्याङ्कन फारम, चार भाषाका टेम्प्लेटसहित प्रमाणपत्रका प्रकार |
| `yust-legacy` | `korean-university` का सबै, साथै भर्ना वर्ष र नर्सिङका लागि क्रेडिट सीमा, सीमाबाहिरका क्रेडिट बैंक विषय, 4.3 ग्रेड स्केल र त्यसको ग्रेडिङ नीति |

प्रोफाइल नभएमा यी प्रशासन प्यानलमा प्रविष्ट गर्नुहोस्। पछि फेरि प्रोफाइल लागू गर्दा प्रशासकले परिवर्तन गरेका मानहरू कायम रहन्छन्। ग्रेड स्केल एक पटक सेट भएपछि परिवर्तन गर्न सकिँदैन (ग्रेड र GPA त्यही स्केलमा राखिन्छन्)।

Django को `createsuperuser` असक्षम गरिएको छ। पहिलो प्रशासक `setup_install` वा `security_create_administrator` बाट मात्र बनाइन्छ ([कमान्ड सन्दर्भ](commands.md))।

स्थापनापछि, कार्यसञ्चालन प्रशासकहरूले [प्रशासक पुस्तिकाको अध्याय 5, प्रारम्भिक सेटअपको क्रम](../admin/05-institution-setup.md) अनुसार सन्दर्भ डेटा प्रविष्ट गर्छन्। सर्भर प्रक्रियाहरू (gunicorn, Celery worker, beat) [डिप्लोय जाँचसूची](deployment-checklist.md) र [निर्धारित कार्यहरू](scheduled-jobs.md) मा वर्णन गरिएअनुसार दर्ता गर्नुहोस्।

### Docker Compose (विकास)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| सेवा | ठेगाना |
|---|---|
| एप्लिकेसन | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (विकासको मेलबक्स) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite dev सर्भर (वैकल्पिक, `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

उत्पादन इमेज `Dockerfile` को `production` target (पूर्वनिर्धारित) हो। यसले बिल्डका बेला `compilemessages` र `collectstatic` चलाउँछ र gunicorn सुरु गर्छ। उही इमेजले worker र beat पनि चलाउँछ (`uv run --no-sync celery -A config worker|beat`)।

## 5. स्थापना प्रमाणित गर्ने

1. `/accounts/login/` मा पहिलो प्रशासकका रूपमा साइन इन गर्नुहोस्। `/admin/` खुल्छ र साइडबारमा **प्रयोगकर्ता र पहुँच**, **अडिट** र **सेटिङ** देखिन्छन्।
2. प्रशासन प्यानलमा **सेटिङ > सुरक्षा** अन्तर्गत दुई-चरण नीति सेट गर्नुहोस्।
3. प्रशासकका लागि दुई-चरण प्रमाणीकरण दर्ता गर्नुहोस् (पोर्टलको **सुरक्षा**, `/portal/security/`)।
4. `uv run manage.py pdf_sample` बाट PDF सेवा जाँच्नुहोस्।
5. प्रशासन प्यानलमा **अडिट > डेटा परिवर्तनहरू** ले स्थापनालाई `system:command:setup_install` का रूपमा देखाउँछ कि भनी जाँच्नुहोस्।
6. `uv run manage.py check --deploy` ले उत्पादनसम्बन्धी कुनै चेतावनी नदिएको र `GET /api/v1/health/` ले `{"status": "ok"}` जवाफ दिएको जाँच्नुहोस् (beat कम्तीमा एक मिनेट चलेको हुनुपर्छ)।

## 6. अद्यावधिक

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

सेवाका नामहरू आफ्नो स्थापनाअनुसार मिलाउनुहोस्। अद्यावधिकको वरिपरिको ब्याकअप र जाँचका लागि [डिप्लोय जाँचसूची](deployment-checklist.md#डिप्लोय-प्रक्रिया) पालना गर्नुहोस्।
