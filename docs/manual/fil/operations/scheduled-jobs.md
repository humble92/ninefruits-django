# Mga naka-iskedyul na job at queue

- Para kanino: mga IT operator
- Kaugnay: [checklist sa deployment](deployment-checklist.md), [integridad ng audit](audit-and-maintenance.md), [sanggunian ng mga command](commands.md)

## Mga pangmatagalang proseso

| Proseso | Command | Pagsusuri |
|---|---|---|
| Web | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| Queue worker | `uv run celery -A config worker --loglevel=INFO` | **Workers** sa Flower, `uv run celery -A config inspect ping` |
| Scheduler | `uv run celery -A config beat --loglevel=INFO` (**eksaktong isang proseso sa kabuuan**) | `scheduler` sa `/api/v1/health/`, ang log ng beat |
| Queue monitor (opsiyonal) | `uv run celery -A config flower --port=5555` | Sa panloob na network lamang o sa likod ng paghihigpit sa access ng Nginx |

Gumagamit ang tatlo ng parehong code at mga environment variable. Halimbawa sa systemd:

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

Gumawa ng isa pang service na ganito rin ang anyo para sa beat na may `ExecStart=... celery -A config beat --loglevel=INFO`. Kahit maraming server, i-enable ang beat service sa isa lamang sa mga ito.

## Mga naka-iskedyul na job

Ang mga pagpaparehistro ay ang `beat_schedule` sa `config/celery.py`; iniaayon dito ng beat ang database scheduler ng django-celery-beat (mga table na `django_celery_beat_*`) kapag nagsisimula ito. Nasa time zone ng server ang mga oras (`APP_TIMEZONE`, UTC bilang default). May hawak na Redis lock (`single_instance`) ang bawat naka-iskedyul na job, kaya hindi kailanman tumatakbo nang dalawang beses nang sabay ang parehong job.

| Job (pangalan sa Celery) | Dalas | Command na gumagawa ng pareho | Pagtukoy sa pagkabigo |
|---|---|---|---|
| `admission.expire_drafts` | Araw-araw nang 03:10 | `admission_expire_drafts` | Pinatatakbo nito ang command mismo, kaya itinatala sa log ng aktibidad ang bawat pagpapatakbo (log na `command`). Kung walang rekord nang mahigit isang araw, suriin ang beat at ang worker |
| `registration.release_reserved_seats` | Bawat 5 minuto | `registration_release_reserved_seats` | Walang rekord ng audit. Kung walang laman pa rin ang `release_processed_at` ng mga paglalaan ng upuan na lumipas na ang oras ng pagpapalaya, suriin ang beat |
| `registration.promote_waitlists` | Bawat oras, sa simula ng oras | `waitlist_promote` | Walang entry sa log ng aktibidad (lumalabas ang mga iniakyat na pagpapatala sa mga pagbabago ng datos bilang `system:task:registration.promote_waitlists`). Ang resulta ng task sa Flower (mga seksiyon, mga pag-akyat) |
| `lms.reconcile` | Araw-araw nang 02:30 | `lms_reconcile` | Mga rekord ng sync bawat link (panel ng administrasyon **Integrasyon ng LMS**), ang resulta ng task sa Flower |
| `audit.seal` | Araw-araw nang 03:30 | `audit_seal` | Sine-seal ang hash chain ng audit ([integridad ng audit](audit-and-maintenance.md)). Suriin kung mas marami sa isang araw na halaga ang hindi pa naka-seal na row na ipinapakita ng `audit_verify_chain` |
| `core.heartbeat` | Bawat minuto | Wala | Isinusulat ang huling oras ng pagtakbo sa cache key na `system:heartbeat`. Sumasagot ang `/api/v1/health/` ng `degraded` kapag lampas 5 minuto na ito |

## Mga queue task

| Task (pangalan sa Celery) | Pinasisimulan ng | Mga tala |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | Isang task bawat batch ng mga rekord (group). Kung nabigo ang isang batch, patakbuhin muli ang command (nilalaktawan ang mga rekord na nasa kasalukuyang key na) |
| `registration.promote_waitlist` | Pag-drop o pag-withdraw sa pagpapatala, pagpapalaya ng paglalaan ng upuan | Isa lamang ang tumatakbo bawat seksiyon (Redis lock, pinipigilan ang mga duplicate). Muling sinusuri ng pag-akyat mula sa waitlist ang bawat panuntunan sa pagpapatala. Ini-queue matapos mag-commit ang transaksiyon |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, pagsasara ng termino sa panel ng administrasyon | Isang chord: mga task na tig-100 mag-aaral, saka ang pangwakas na task (ranggo ng karangalan, pagbabago ng katayuan ng termino, pag-abiso sa kawaning nagsimula nito). Ang progreso ay ang row ng `job_batches` na `term-close:{term code}`, na ipinapakita sa panel ng administrasyon. Sumusubok muli ang isang batch task nang hanggang 3 beses sa mga error ng database; kung nabibigo pa rin, minamarkahang nabigo ang buong batch at hindi tumatakbo ang pangwakas na task. Ayusin ang sanhi, saka simulan muli ang pagsasara ng termino (pareho ang resulta ng mga kalkulasyon bawat mag-aaral kapag pinatakbo muli) |
| `importing.import_chunk` | Pag-import ng CSV sa panel ng administrasyon, `reference_import` | Isang task bawat chunk. Mga resulta sa `imports`, mga nabigong row sa `failed_import_rows` (mga resulta ng pag-import sa panel ng administrasyon) |
| `lms.sync_section`, `lms.sync_enrollment` | Mga event ng pagbabago ng seksiyon at pagpapatala | Kapag nabigo, sinusubukang muli nang hanggang 3 beses na may isang minutong pagitan. Inaayos ng gabi-gabing `lms.reconcile` ang natitira |

Habang tumatakbo ang isang task, itinatala ang DB actor bilang `system:task:{task name}` (halimbawa `system:task:grading.close_term_records`), kasama ang request ID at ang user ng request na nag-queue nito.

Ipinapakita ng Flower ang mga nabigong task (**Tasks**, state na `FAILURE`) at ang mga exception nito. Gumagamit ng `acks_late` ang mga Celery task, kaya muling tumatakbo ang task na naantala dahil namatay ang worker. Ginawa ang bawat task para magbigay ng parehong resulta kapag pinatakbo muli (idempotent).
