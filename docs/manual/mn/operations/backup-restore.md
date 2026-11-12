# Нөөцлөлт ба сэргээлт

- Зориулалт: МТ-ийн ашиглалтын ажилтнууд
- Холбогдох: [суулгалт](installation.md), [түлхүүрийн удирдлага](security-keys.md), [аудитын бүрэн бүтэн байдал](audit-and-maintenance.md)

## Нөөцлөх зүйлс

| Объект | Арга | Давтамж (зөвлөмж) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` эсвэл PITR (WAL архивлалт) | Өдөр бүр бүтэн + тасралтгүй WAL |
| Хувийн файлын хадгалалт (`PRIVATE_MEDIA_ROOT`, анхдагч `storage/private`) | Snapshot эсвэл хувилбартай bucket | DB-тэй адил |
| Орчны тохиргоо ба түлхүүрүүд (`DJANGO_SECRET_KEY`, `PII_*`, DB-ийн нууц үг) | Нууц хадгалалт | Өөрчлөлт бүрд |

DB болон файлын хадгалалтыг ижил цэгт сэргээх боломжтой байх ёстой (зураг, өргөдлийн баримт, тодорхойлолтын PDF, шалгалтын нотлох баримтын мета өгөгдөл DB-ийн `media` хүснэгтэд байдаг). Redis-ийг нөөцлөхгүй: тэнд зөвхөн кэш, түгжээ, дараалал байх бөгөөд сессүүд мөн DB-д (`django_session`) хадгалагдана. Төлөвлөгдсөн ажлын жагсаалт (django-celery-beat) ч DB-д байх бөгөөд beat эхлэхдээ түүнийг `config/celery.py`-тэй дахин тааруулна.

`staticfiles/` болон `static/dist/` нь бүтээлтийн гаралт тул нөөцлөхгүй (`npm run build` болон `collectstatic` тэдгээрийг дахин үүсгэнэ).

## DB нөөцлөх жишээ

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` бүх схемийг (`public`, `audit`, `reporting`, `util`) эзэмшдэг тул энэ бүртгэлээр нөөцөлнө. Ролиуд (`app_*`) нь кластерын объект тул dump-д ордоггүй. Сэргээх сервер дээр эхлээд [Суулгалт](installation.md)-ын 2-р хэсэгт заасны дагуу ролиудыг үүсгэнэ.

Нөөцлөхөөс өмнө `uv run manage.py audit_verify_chain`-ийг ажиллуулбал сэргээсэн DB дээр ижил командаар аудитын гинжийг харьцуулж болно.

## Сэргээх жишээ

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

Сэргээсэн DB дээр аппликейшныг ажиллуулахын тулд `DB_DATABASE=ninefruits_restore` болон **нөөцлөх үеийн түлхүүрүүдийг** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, түүнээс хойш түлхүүр солигдсон бол `PII_PREVIOUS_KEYS`) тохируулна. Дараа нь төлөвийг шалгана:

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

`migrate --check` хэрэгжүүлэх миграц мэдээлбэл нөөц нь одоогийн кодоос хуучин байна. Ижил хувилбарын кодоор сэргээх эсвэл `setup_install --force`-оор шинэчилнэ.

## Сэргээх дадлага

Улирал бүр (гурван сар тутам) тусдаа сервер дээр сэргээж дараахыг шалгана: нэвтрэх, хувийн мэдээллийг тайлах (удирдлагын самбарт хувь хүний **Регистрийн дугаар харах**; түлхүүр таарч байгаа эсэх), аудитын бичлэг харах болон `audit_verify_chain`, файл нээх (зураг, тодорхойлолтын PDF), тодорхойлолт баталгаажуулах хуудас. Үр дүнг (зарцуулсан хугацаа, асуудал) тэмдэглэнэ.
