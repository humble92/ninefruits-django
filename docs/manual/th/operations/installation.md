# การติดตั้ง

- ผู้อ่าน: ผู้ดูแลระบบไอที
- เกี่ยวข้อง: [คู่มือคำสั่ง](commands.md), [การจัดการคีย์](security-keys.md), [รายการตรวจสอบการนำขึ้นใช้งาน](deployment-checklist.md)

## 1. ข้อกำหนดของระบบ

| องค์ประกอบ | เวอร์ชัน | หมายเหตุ |
|---|---|---|
| Python | 3.14 | ติดตั้งและรันด้วย [uv](https://docs.astral.sh/uv/) (`uv sync`) แพ็กเกจระบบ: `gettext` (คอมไพล์คำแปล) `libmagic` (ตรวจจับประเภทไฟล์) |
| Node.js | 22 | build แอสเซ็ตของหน้าจอ (`npm ci && npm run build`) เซิร์ฟเวอร์ระบบใช้งานจริงต้องการเพียงผลลัพธ์จากการ build |
| PostgreSQL | 18 | ส่วนขยาย `btree_gist`, `pg_trgm` (ติดตั้งโดยไมเกรชัน) collation แบบ ICU |
| Redis | 8 | แคช เซสชัน broker และผลลัพธ์ของ Celery |
| Gotenberg | 8 | การสร้าง PDF เปิดเฉพาะในเครือข่ายภายใน |
| เซิร์ฟเวอร์อีเมล | SMTP | การตั้งรหัสผ่านใหม่ รหัสยืนยันตัวตนแบบสองขั้นตอนทางอีเมล คำเชิญ การแจ้งเตือน |
| เว็บเซิร์ฟเวอร์ | gunicorn + Nginx | `uv run gunicorn config.wsgi -c config/gunicorn.py` Nginx ให้บริการ `staticfiles/` เอง และส่งต่อคำขออื่นทั้งหมดไปยัง gunicorn |
| ตัวประมวลผลคิว | Celery worker | ให้ `uv run celery -A config worker` ทำงานต่อเนื่องภายใต้ตัวจัดการโพรเซส (systemd, supervisor) |
| ตัวจัดกำหนดเวลา | Celery beat | รัน `uv run celery -A config beat` บนเครื่อง **เดียวเท่านั้น** (ตัวจัดกำหนดเวลาแบบฐานข้อมูล django-celery-beat) |
| ตัวติดตามคิว | Flower (ไม่บังคับ) | `uv run celery -A config flower` ให้อยู่ในเครือข่ายภายในหรือหลังการจำกัดการเข้าถึงของ Nginx (หรือ `--basic-auth` ของ Flower) ห้ามเปิดสู่ภายนอก |

## 2. การเตรียมฐานข้อมูล

รันครั้งเดียวด้วย superuser ของฐานข้อมูล แอปพลิเคชันไม่ใช้ superuser เลย

```bash
createdb -U postgres ninefruits
psql -U postgres -d postgres -v ON_ERROR_STOP=1 \
     -v migrator_password='...' -v runtime_password='...' -v reporting_password='...' \
     -f db/sql/roles/create_roles.sql
psql -U postgres -d ninefruits -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
```

| บทบาท | ตัวแปรสภาพแวดล้อม | วัตถุประสงค์ |
|---|---|---|
| `app_runtime` | `DB_USERNAME`, `DB_PASSWORD` | การทำงานของแอปพลิเคชัน (ใช้ความปลอดภัยระดับแถว ไม่มี DDL) |
| `app_migrator` | `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | ไมเกรชัน การผนึกและการลบบันทึกการตรวจสอบเท่านั้น (`migrate` ใช้การเชื่อมต่อนี้โดยอัตโนมัติ) |
| `app_reporting` | (ตั้งค่าในเครื่องมือ BI) | การอ่านสคีมา `reporting` |

ในสภาพแวดล้อมพัฒนาแบบ Docker Compose `docker/pgsql/20-create-app-roles.sh` จะทำสิ่งเดียวกันเมื่อคอนเทนเนอร์ `pgsql` เริ่มทำงานครั้งแรก (บทบาท ฐานข้อมูล `ninefruits` และฐานข้อมูลทดสอบ)

## 3. การตั้งค่าสภาพแวดล้อม

คัดลอก `.env.example` เป็น `.env` แล้วกรอกค่า (ในระบบใช้งานจริง ให้ส่งเป็นตัวแปรสภาพแวดล้อมหรือจากที่จัดเก็บข้อมูลลับ) ค่าที่ต้องเปลี่ยน:

- `DJANGO_ENV=production`, `DJANGO_SETTINGS_MODULE=config.settings.production`, `DJANGO_DEBUG=false`, `APP_URL`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DJANGO_SECRET_KEY`: `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` จัดเก็บตามที่อธิบายใน [การจัดการคีย์](security-keys.md)
- `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`: `uv run manage.py pii_generate_key` **หากสูญหาย จะกู้คืนข้อมูลส่วนบุคคลที่เข้ารหัสไว้ไม่ได้** จัดเก็บแยกต่างหากตามที่อธิบายใน [การจัดการคีย์](security-keys.md)
- `DB_*`, `REDIS_URL`, `MAIL_*`, `GOTENBERG_URL`
- `TRUSTED_PROXY_COUNT`: จำนวน reverse proxy หน้าแอปพลิเคชัน (`1` สำหรับ Nginx ตัวเดียว) ดู [รายการตรวจสอบการนำขึ้นใช้งาน](deployment-checklist.md#พร็อกซีและที่อยู่ของไคลเอนต์)
- `INSTITUTION_TIMEZONE`: เขตเวลาเริ่มต้นของสถาบันสำหรับการติดตั้งครั้งแรก (เช่น `Asia/Seoul`)

รายการตัวแปรสภาพแวดล้อมของระบบใช้งานจริงทั้งหมดอยู่ใน [รายการตรวจสอบการนำขึ้นใช้งาน](deployment-checklist.md#ตัวแปรสภาพแวดล้อม)

## 4. การติดตั้ง

```bash
uv sync --frozen --no-dev
npm ci && npm run build                     # static/dist/ (manifest.json)
uv run manage.py compilemessages --ignore=.venv
uv run manage.py collectstatic --noinput
uv run manage.py setup_install              # answers the questions as it goes
```

`setup_install` ดำเนินการตามลำดับ: ไมเกรชัน (ผ่านการเชื่อมต่อ `app_migrator`) ข้อมูลพื้นฐานที่จำเป็น (แม่แบบบทบาทและการซิงค์สิทธิ์ ประเทศ ภาษา ประเภทรายการรหัส ประเภทหน่วยงาน ประเภทการเปลี่ยนสถานภาพ ชุดกฎการลงทะเบียน) ค่าเริ่มต้นของสถาบัน (ภาษาเริ่มต้น เขตเวลา ชื่อสถาบัน) การกำหนดเกณฑ์ระดับคะแนน โปรไฟล์การติดตั้ง และผู้ดูแลระบบคนแรก ในสคริปต์การนำขึ้นใช้งานให้รันด้วย `--force` และตัวเลือก รหัสผ่านของผู้ดูแลระบบจะอ่านจาก standard input

```bash
echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=en --timezone=Asia/Seoul \
    --institution-name="Example University" --profile=korean-university --grade-scale=4.5 \
    --admin-email=admin@example.ac.kr --admin-name="Administrator"
```

โปรไฟล์การติดตั้ง (`--profile=` ระบุได้มากกว่าหนึ่งครั้ง)

| คีย์ | เนื้อหา |
|---|---|
| `korean-university` | ประเภทภาคการศึกษาฤดูใบไม้ผลิ/ฤดูร้อน/ฤดูใบไม้ร่วง/ฤดูหนาว เกณฑ์ระดับคะแนน 4.5 หมวดวิชา คาบเรียนตั้งแต่ 09:00 ประเภทห้อง ประเภทการรับสมัครและเอกสารประกอบการสมัคร แบบประเมินรายวิชาเริ่มต้น ประเภทหนังสือรับรองพร้อมแม่แบบสี่ภาษา |
| `yust-legacy` | ทุกอย่างใน `korean-university` รวมทั้งเกณฑ์หน่วยกิตตามปีที่เข้าศึกษาและสำหรับคณะพยาบาลศาสตร์ รายวิชาในธนาคารหน่วยกิตที่ไม่นับในเกณฑ์ เกณฑ์ระดับคะแนน 4.3 และนโยบายการวัดผล |

หากไม่ใช้โปรไฟล์ ให้กรอกข้อมูลเหล่านี้ในแผงผู้ดูแลระบบ การใช้โปรไฟล์ซ้ำในภายหลังจะคงค่าที่ผู้ดูแลระบบเปลี่ยนไว้ เกณฑ์ระดับคะแนนเปลี่ยนไม่ได้เมื่อกำหนดแล้ว (เกรดและเกรดเฉลี่ยจัดเก็บตามเกณฑ์นั้น)

`createsuperuser` ของ Django ถูกปิดใช้งาน ผู้ดูแลระบบคนแรกสร้างได้เฉพาะด้วย `setup_install` หรือ `security_create_administrator` ([คู่มือคำสั่ง](commands.md))

หลังการติดตั้ง ผู้ดูแลงานบริหารจะกรอกข้อมูลอ้างอิงตาม [คู่มือผู้ดูแลระบบ บทที่ 5 ลำดับการตั้งค่าเริ่มต้น](../admin/05-institution-setup.md) ลงทะเบียนโพรเซสของเซิร์ฟเวอร์ (gunicorn, Celery worker, beat) ตามที่อธิบายใน [รายการตรวจสอบการนำขึ้นใช้งาน](deployment-checklist.md) และ [งานตามกำหนดเวลา](scheduled-jobs.md)

### Docker Compose (การพัฒนา)

```bash
cp .env.example .env                        # fill the PII keys with the output of the command below
docker compose up -d                        # app, worker, beat, flower, pgsql, redis, mailpit, gotenberg
docker compose exec app uv run manage.py pii_generate_key
docker compose exec app uv run manage.py setup_install --profile=korean-university --grade-scale=4.5
docker compose exec app uv run manage.py compilemessages --ignore=.venv
docker compose exec app uv run manage.py setup_demo --size=small --seed=42   # optional: demo data
```

| บริการ | ที่อยู่ |
|---|---|
| แอปพลิเคชัน | `http://localhost:8000/portal/`, `http://localhost:8000/admin/` |
| Mailpit (กล่องจดหมายสำหรับการพัฒนา) | `http://localhost:8025` |
| Flower | `http://localhost:5555` |
| Vite dev server (ไม่บังคับ `docker compose --profile vite up -d`, `VITE_DEV_MODE=true`) | `http://localhost:5173` |

อิมเมจสำหรับระบบใช้งานจริงคือ target `production` ของ `Dockerfile` (ค่าเริ่มต้น) ซึ่งรัน `compilemessages` และ `collectstatic` ตอน build และเริ่ม gunicorn อิมเมจเดียวกันใช้รัน worker และ beat (`uv run --no-sync celery -A config worker|beat`)

## 5. การตรวจสอบการติดตั้ง

1. เข้าสู่ระบบเป็นผู้ดูแลระบบคนแรกที่ `/accounts/login/` `/admin/` จะเปิดได้ และแถบด้านข้างแสดง **ผู้ใช้และสิทธิ์การเข้าถึง** **การตรวจสอบ** และ **การตั้งค่า**
2. ในแผงผู้ดูแลระบบ ตั้งค่านโยบายการยืนยันตัวตนแบบสองขั้นตอนที่ **การตั้งค่า > ความปลอดภัย**
3. ลงทะเบียนการยืนยันตัวตนแบบสองขั้นตอนสำหรับผู้ดูแลระบบ (**ความปลอดภัย** ในพอร์ทัล `/portal/security/`)
4. ตรวจสอบบริการ PDF ด้วย `uv run manage.py pdf_sample`
5. ในแผงผู้ดูแลระบบ ตรวจสอบว่า **การตรวจสอบ > การเปลี่ยนแปลงข้อมูล** แสดงการติดตั้งเป็น `system:command:setup_install`
6. ตรวจสอบว่า `uv run manage.py check --deploy` ไม่รายงานคำเตือนของระบบใช้งานจริง และ `GET /api/v1/health/` ตอบ `{"status": "ok"}` (beat ต้องทำงานมาแล้วหนึ่งนาที)

## 6. การอัปเดต

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

ปรับชื่อบริการให้ตรงกับการติดตั้งของท่าน ปฏิบัติตาม [รายการตรวจสอบการนำขึ้นใช้งาน](deployment-checklist.md#ขั้นตอนการนำขึ้นใช้งาน) สำหรับการสำรองข้อมูลและการตรวจสอบก่อนและหลังการอัปเดต
