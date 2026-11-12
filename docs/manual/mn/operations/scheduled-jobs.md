# Төлөвлөгдсөн ажил ба дараалал

- Зориулалт: МТ-ийн ашиглалтын ажилтнууд
- Холбогдох: [байршуулалтын хяналтын хуудас](deployment-checklist.md), [аудитын бүрэн бүтэн байдал](audit-and-maintenance.md), [командын лавлах](commands.md)

## Тасралтгүй ажиллах процессууд

| Процесс | Команд | Шалгах |
|---|---|---|
| Веб | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| Дарааллын worker | `uv run celery -A config worker --loglevel=INFO` | Flower дахь **Workers**, `uv run celery -A config inspect ping` |
| Төлөвлөгч | `uv run celery -A config beat --loglevel=INFO` (**нийтдээ яг нэг процесс**) | `/api/v1/health/` дахь `scheduler`, beat-ийн лог |
| Дарааллын монитор (сонголтоор) | `uv run celery -A config flower --port=5555` | Зөвхөн дотоод сүлжээнд эсвэл Nginx-ийн хандалтын хязгаарлалтын ард |

Гурвуулаа ижил код болон орчны хувьсагчийг ашиглана. systemd-ийн жишээ:

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

Beat-д ижил хэлбэрийн дахиад нэг үйлчилгээг `ExecStart=... celery -A config beat --loglevel=INFO`-тэйгээр үүсгэнэ. Олон сервертэй байсан ч beat үйлчилгээг зөвхөн нэг дээр нь идэвхжүүлнэ.

## Төлөвлөгдсөн ажлууд

Бүртгэл нь `config/celery.py` дахь `beat_schedule`; beat эхлэхдээ django-celery-beat-ийн өгөгдлийн сангийн төлөвлөгчийг (`django_celery_beat_*` хүснэгтүүд) түүнтэй тааруулна. Цагийг серверийн цагийн бүсээр (`APP_TIMEZONE`, анхдагч UTC) заана. Төлөвлөгдсөн ажил бүр Redis-ийн түгжээ (`single_instance`) барьдаг тул нэг ажил хэзээ ч зэрэг хоёр удаа ажиллахгүй.

| Ажил (Celery нэр) | Давтамж | Ижил үйлдэл хийх команд | Алдааг илрүүлэх |
|---|---|---|---|
| `admission.expire_drafts` | Өдөр бүр 03:10 | `admission_expire_drafts` | Командыг өөрийг нь ажиллуулдаг тул ажиллах бүр үйлдлийн бүртгэлд (log `command`) бичигдэнэ. Нэг өдрөөс илүү хугацаанд бичлэг байхгүй бол beat болон worker-ийг шалгана |
| `registration.release_reserved_seats` | 5 минут тутам | `registration_release_reserved_seats` | Аудитын бичлэггүй. Чөлөөлөх цаг нь өнгөрсөн суудлын хуваарилалтын `release_processed_at` хоосон хэвээр байвал beat-ийг шалгана |
| `registration.promote_waitlists` | Цаг тутам, цаг болоход | `waitlist_promote` | Үйлдлийн бүртгэлд бичлэггүй (дэвшүүлсэн хичээлийн бүртгэл өгөгдлийн өөрчлөлтөд `system:task:registration.promote_waitlists` гэж харагдана). Flower дахь ажлын үр дүн (бүлэг, дэвшүүлэлт) |
| `lms.reconcile` | Өдөр бүр 02:30 | `lms_reconcile` | Холбоос тус бүрийн синхрончлолын бичлэг (удирдлагын самбарын **LMS холболт**), Flower дахь ажлын үр дүн |
| `audit.seal` | Өдөр бүр 03:30 | `audit_seal` | Аудитын хэш гинжийг битүүмжилнэ ([аудитын бүрэн бүтэн байдал](audit-and-maintenance.md)). `audit_verify_chain` нэг өдрийнхөөс олон битүүмжлэгдээгүй мөр харуулбал шалгана |
| `core.heartbeat` | Минут тутам | Байхгүй | Сүүлд ажилласан цагийг кэшийн `system:heartbeat` түлхүүрт бичнэ. 5 минутаас хуучин бол `/api/v1/health/` `degraded` гэж хариулна |

## Дарааллын ажлууд

| Ажил (Celery нэр) | Эхлүүлэгч | Тайлбар |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | Бичлэгийн багц тус бүрт нэг ажил (group). Багц амжилтгүй болбол командыг дахин ажиллуулна (одоогийн түлхүүр дээр байгаа бичлэгүүдийг алгасна) |
| `registration.promote_waitlist` | Хичээлийн бүртгэлийг хасах эсвэл цуцлах, суудлын хуваарилалтыг чөлөөлөх | Бүлэг тус бүрд зөвхөн нэг нь ажиллана (Redis-ийн түгжээ, давхардлаас сэргийлнэ). Хүлээлгийн жагсаалтаас дэвшүүлэхдээ хичээл сонголтын бүх дүрмийг дахин шалгана. Гүйлгээ commit болсны дараа дараалалд орно |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, удирдлагын самбарт улирал хаах | Chord: 100 оюутны ажлууд, дараа нь дуусгах ажил (онц сурлагын эрэмбэ, улирлын төлөвийн өөрчлөлт, эхлүүлсэн ажилтанд мэдэгдэх). Явц нь `job_batches`-ийн `term-close:{term code}` мөр бөгөөд удирдлагын самбарт харагдана. Багцын ажил өгөгдлийн сангийн алдаанд 3 хүртэл удаа дахин оролдоно; дахиад амжилтгүй бол багц бүхэлдээ амжилтгүй гэж тэмдэглэгдэж, дуусгах ажил ажиллахгүй. Шалтгааныг засаад улирал хаахыг дахин эхлүүлнэ (оюутан тус бүрийн тооцоолол дахин ажиллуулахад ижил үр дүн өгнө) |
| `importing.import_chunk` | Удирдлагын самбар дахь CSV оруулалт, `reference_import` | Хэсэг тус бүрт нэг ажил. Үр дүн `imports`-д, амжилтгүй мөрүүд `failed_import_rows`-д (удирдлагын самбар дахь оруулгын үр дүн) |
| `lms.sync_section`, `lms.sync_enrollment` | Бүлэг болон хичээлийн бүртгэлийн өөрчлөлтийн үйл явдал | Амжилтгүй бол минутын зайтай 3 хүртэл удаа дахин оролдоно. Үлдсэнийг шөнийн `lms.reconcile` засна |

Ажил ажиллаж байх үед DB-ийн гүйцэтгэгчийг `system:task:{task name}` (жишээ нь `system:task:grading.close_term_records`) гэж, түүнийг дараалалд оруулсан хүсэлтийн ID болон хэрэглэгчийн хамт бүртгэнэ.

Flower амжилтгүй ажлууд (**Tasks**, төлөв `FAILURE`) болон тэдгээрийн exception-ийг харуулна. Celery-ийн ажлууд `acks_late` ашигладаг тул worker унасны улмаас тасарсан ажил дахин ажиллана. Ажил бүр дахин ажиллуулахад ижил үр дүн өгөхөөр (idempotent) бүтээгдсэн.
