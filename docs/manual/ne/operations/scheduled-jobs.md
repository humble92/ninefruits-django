# निर्धारित कार्यहरू र क्युहरू

- लक्षित पाठक: IT सञ्चालकहरू
- सम्बन्धित: [डिप्लोय जाँचसूची](deployment-checklist.md), [अडिट अखण्डता](audit-and-maintenance.md), [कमान्ड सन्दर्भ](commands.md)

## लामो समय चल्ने प्रक्रियाहरू

| प्रक्रिया | कमान्ड | जाँच |
|---|---|---|
| वेब | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| क्यु worker | `uv run celery -A config worker --loglevel=INFO` | Flower को **Workers**, `uv run celery -A config inspect ping` |
| अनुसूचक | `uv run celery -A config beat --loglevel=INFO` (**समग्रमा ठ्याक्कै एउटा प्रक्रिया**) | `/api/v1/health/` को `scheduler`, beat को लग |
| क्यु मनिटर (वैकल्पिक) | `uv run celery -A config flower --port=5555` | आन्तरिक नेटवर्कमा वा Nginx पहुँच प्रतिबन्ध पछाडि मात्र |

तीनैले उही कोड र वातावरण चर प्रयोग गर्छन्। systemd को उदाहरण:

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

beat का लागि `ExecStart=... celery -A config beat --loglevel=INFO` सहित उही आकारको अर्को सेवा बनाउनुहोस्। धेरै सर्भर भए पनि beat सेवा तीमध्ये एउटामा मात्र सक्षम गर्नुहोस्।

## निर्धारित कार्यहरू

दर्ताहरू `config/celery.py` को `beat_schedule` हुन्; beat सुरु हुँदा django-celery-beat डेटाबेस अनुसूचक (`django_celery_beat_*` तालिकाहरू) लाई त्यससँग मिलाउँछ। समयहरू सर्भरको समय क्षेत्र (`APP_TIMEZONE`, पूर्वनिर्धारित UTC) मा हुन्छन्। हरेक निर्धारित कार्यले Redis lock (`single_instance`) राख्छ, त्यसैले उही कार्य एकैसाथ कहिल्यै दुई पटक चल्दैन।

| कार्य (Celery नाम) | आवृत्ति | उही काम गर्ने कमान्ड | असफलता पत्ता लगाउने |
|---|---|---|---|
| `admission.expire_drafts` | हरेक दिन 03:10 मा | `admission_expire_drafts` | कमान्ड आफैँ चलाउँछ, त्यसैले हरेक रन गतिविधि लग (लग `command`) मा अभिलेख हुन्छ। एक दिनभन्दा बढी अभिलेख नभएमा beat र worker जाँच्नुहोस् |
| `registration.release_reserved_seats` | हरेक 5 मिनेटमा | `registration_release_reserved_seats` | अडिट अभिलेख छैन। खुल्ने समय नाघेका सिट बाँडफाँडको `release_processed_at` अझै खाली भएमा beat जाँच्नुहोस् |
| `registration.promote_waitlists` | हरेक घण्टा, ठ्याक्कै घण्टामा | `waitlist_promote` | गतिविधि लग प्रविष्टि छैन (दर्ता गरिएका भर्नाहरू डेटा परिवर्तनमा `system:task:registration.promote_waitlists` का रूपमा देखिन्छन्)। Flower मा कार्यको नतिजा (सेक्सन, दर्ता) |
| `lms.reconcile` | हरेक दिन 02:30 मा | `lms_reconcile` | प्रति लिङ्क सिङ्क अभिलेख (प्रशासन प्यानलको **LMS एकीकरण**), Flower मा कार्यको नतिजा |
| `audit.seal` | हरेक दिन 03:30 मा | `audit_seal` | अडिट ह्यास चेन सिल गर्छ ([अडिट अखण्डता](audit-and-maintenance.md))। `audit_verify_chain` ले एक दिनभन्दा बढीका सिल नगरिएका पङ्क्ति देखाएमा जाँच्नुहोस् |
| `core.heartbeat` | हरेक मिनेट | छैन | अन्तिम रनको समय क्यास कुञ्जी `system:heartbeat` मा लेख्छ। त्यो 5 मिनेटभन्दा पुरानो हुँदा `/api/v1/health/` ले `degraded` जवाफ दिन्छ |

## क्यु कार्यहरू

| कार्य (Celery नाम) | कसले सुरु गर्छ | टिप्पणी |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | अभिलेखको प्रति समूह एउटा कार्य (group)। कुनै समूह असफल भएमा कमान्ड फेरि चलाउनुहोस् (पहिले नै हालको कुञ्जीमा भएका अभिलेख छोडिन्छन्) |
| `registration.promote_waitlist` | भर्ना हटाउने वा परित्याग, सिट बाँडफाँड खुला | प्रति सेक्सन एउटा मात्र चल्छ (Redis lock, दोहोरो रोकिन्छ)। प्रतीक्षा सूचीबाट दर्ताले हरेक विषय दर्ता नियम फेरि जाँच्छ। ट्रान्ज्याक्सन commit भएपछि क्युमा राखिन्छ |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, प्रशासन प्यानलमा सेमेस्टर बन्द | chord: 100 विद्यार्थीका कार्यहरू, त्यसपछि अन्तिम कार्य (सम्मानको क्रम, सेमेस्टरको स्थिति परिवर्तन, सुरु गर्ने कर्मचारीलाई सूचना)। प्रगति `job_batches` को पङ्क्ति `term-close:{term code}` हो, प्रशासन प्यानलमा देखाइन्छ। batch कार्य डेटाबेस त्रुटिमा 3 पटकसम्म फेरि प्रयास गर्छ; त्यसपछि पनि असफल भएमा पूरा batch असफल चिन्ह लगाइन्छ र अन्तिम कार्य चल्दैन। कारण सच्याएर सेमेस्टर बन्द फेरि सुरु गर्नुहोस् (प्रति विद्यार्थी गणनाले फेरि चलाउँदा उही नतिजा दिन्छ) |
| `importing.import_chunk` | प्रशासन प्यानलमा CSV आयात, `reference_import` | प्रति समूह एउटा कार्य। नतिजा `imports` मा, असफल पङ्क्ति `failed_import_rows` मा (प्रशासन प्यानलका आयात नतिजा) |
| `lms.sync_section`, `lms.sync_enrollment` | सेक्सन र भर्ना परिवर्तनका घटना | असफल भएमा एक मिनेटको फरकमा 3 पटकसम्म फेरि प्रयास। बाँकी रहेको कुरा रातिको `lms.reconcile` ले सच्याउँछ |

कार्य चलिरहँदा DB कर्ता `system:task:{task name}` (उदाहरणका लागि `system:task:grading.close_term_records`) का रूपमा, त्यसलाई क्युमा राख्ने अनुरोधको अनुरोध ID र प्रयोगकर्तासहित अभिलेख हुन्छ।

Flower ले असफल कार्यहरू (**Tasks**, अवस्था `FAILURE`) र तिनका exception देखाउँछ। Celery कार्यहरूले `acks_late` प्रयोग गर्छन्, त्यसैले worker मर्दा बीचमा रोकिएको कार्य फेरि चल्छ। हरेक कार्य फेरि चलाउँदा उही नतिजा दिने गरी (idempotent) बनाइएको छ।
