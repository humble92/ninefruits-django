# ब्याकअप र पुनर्स्थापना

- लक्षित पाठक: IT सञ्चालकहरू
- सम्बन्धित: [स्थापना](installation.md), [कुञ्जी व्यवस्थापन](security-keys.md), [अडिट अखण्डता](audit-and-maintenance.md)

## के ब्याकअप गर्ने

| लक्ष्य | तरिका | आवृत्ति (सिफारिस) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` वा PITR (WAL archiving) | दैनिक पूर्ण + निरन्तर WAL |
| निजी फाइल भण्डारण (`PRIVATE_MEDIA_ROOT`, पूर्वनिर्धारित `storage/private`) | Snapshot वा संस्करणसहितको bucket | DB कै जस्तो |
| वातावरण कन्फिगरेसन र कुञ्जीहरू (`DJANGO_SECRET_KEY`, `PII_*`, DB पासवर्ड) | गोप्य भण्डार | हरेक परिवर्तनमा |

DB र फाइल भण्डारण एउटै समयबिन्दुमा पुनर्स्थापना गर्न मिल्ने हुनुपर्छ (फोटो, आवेदनका कागजात, प्रमाणपत्र PDF र परीक्षाका प्रमाणको मेटाडेटा DB तालिका `media` मा रहन्छ)। Redis ब्याकअप गरिँदैन: यसमा क्यास, lock र क्यु मात्र हुन्छन्, र सत्रहरू DB (`django_session`) मा पनि राखिन्छन्। निर्धारित कार्यहरूको सूची (django-celery-beat) पनि DB मा हुन्छ, र beat सुरु हुँदा त्यसलाई `config/celery.py` सँग फेरि मिलाउँछ।

`staticfiles/` र `static/dist/` बिल्ड आउटपुट हुन् र ब्याकअप गरिँदैनन् (`npm run build` र `collectstatic` ले तिनलाई फेरि बनाउँछन्)।

## DB ब्याकअपको उदाहरण

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` सबै स्किमा (`public`, `audit`, `reporting`, `util`) को मालिक हो, त्यसैले यही खाताबाट ब्याकअप लिनुहोस्। भूमिकाहरू (`app_*`) cluster वस्तु हुन् र डम्पमा पर्दैनन्। पुनर्स्थापना सर्भरमा पहिले [स्थापना](installation.md) को खण्ड 2 मा वर्णन गरिएअनुसार भूमिकाहरू बनाउनुहोस्।

ब्याकअपअघि `uv run manage.py audit_verify_chain` चलाउनुभयो भने पुनर्स्थापित DB मा उही कमान्ड चलाएर अडिट चेनहरू दाँज्न सकिन्छ।

## पुनर्स्थापनाको उदाहरण

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

पुनर्स्थापित DB मा एप्लिकेसन चलाउन `DB_DATABASE=ninefruits_restore` र **ब्याकअपको समयका कुञ्जीहरू** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, र त्यसपछि कुञ्जी परिवर्तन भएको भए `PII_PREVIOUS_KEYS`) सेट गर्नुहोस्। त्यसपछि अवस्था जाँच्नुहोस्:

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

`migrate --check` ले लागू गर्नुपर्ने migration देखाएमा ब्याकअप हालको कोडभन्दा पुरानो हो। उही संस्करणको कोडसहित पुनर्स्थापना गर्नुहोस्, वा `setup_install --force` बाट अपग्रेड गर्नुहोस्।

## पुनर्स्थापना अभ्यास

हरेक त्रैमासिकमा छुट्टै सर्भरमा पुनर्स्थापना गरेर प्रमाणित गर्नुहोस्: साइन इन, व्यक्तिगत डेटाको डिक्रिप्सन (प्रशासन प्यानलमा कुनै व्यक्तिको **राष्ट्रिय परिचयपत्र नम्बर देखाउनुहोस्**; कुञ्जी मेल खान्छ), अडिट अभिलेख हेर्ने र `audit_verify_chain`, फाइल खोल्ने (फोटो, प्रमाणपत्र PDF), प्रमाणपत्र प्रमाणीकरण पृष्ठ। नतिजा (लागेको समय, समस्या) अभिलेख गर्नुहोस्।
