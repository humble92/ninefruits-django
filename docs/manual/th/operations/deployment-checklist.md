# รายการตรวจสอบการนำขึ้นใช้งานและการตั้งค่า gunicorn และ Python

- ผู้อ่าน: ผู้ดูแลระบบไอที
- เกี่ยวข้อง: [การติดตั้ง](installation.md), [การจัดการคีย์](security-keys.md), [งานตามกำหนดเวลา](scheduled-jobs.md), [การทดสอบโหลด](load-testing.md)

## Python และ dependency

- ใช้รุ่นแพตช์ล่าสุดของ **Python 3.14** เมื่อสร้างอิมเมจคอนเทนเนอร์หรือเซิร์ฟเวอร์ อย่าตรึงเวอร์ชันแพตช์ของ Python ให้ใช้รุ่นล่าสุด (`python:3.14-slim` ใน `Dockerfile`)
- dependency ของ Python ถูกล็อกไว้ใน `uv.lock` การติดตั้งในระบบใช้งานจริงใช้ `uv sync --frozen --no-dev` เสมอ (จะล้มเหลวหากไฟล์ล็อกไม่ตรงกัน) เครื่องมือพัฒนา (pytest, ruff, mypy, Playwright) จะไม่ไปถึงระบบใช้งานจริง
- เมื่อ Django ออกรุ่นแก้ไขความปลอดภัย ให้อัปเกรดด้วย `uv lock --upgrade-package django` รันการทดสอบแล้วนำขึ้นใช้งาน ตรวจสอบช่องโหว่ของ dependency แบบเดียวกับ CI: `uv export --frozen --no-emit-project --format requirements-txt > /tmp/requirements.txt && uv run pip-audit --strict --disable-pip -r /tmp/requirements.txt`
- `uv run manage.py check --deploy` เตือนเกี่ยวกับการตั้งค่าระบบใช้งานจริง (`DEBUG`, HTTPS คุกกี้ HSTS ความยาวคีย์ลับ) การนำขึ้นใช้งานทุกครั้งต้องไม่มีคำเตือน

## gunicorn และ Nginx

| รายการ | ค่า | เหตุผล |
|---|---|---|
| การรัน gunicorn | `uv run gunicorn config.wsgi -c config/gunicorn.py` | WSGI, worker แบบ sync จำนวน worker และขนาดพูลการเชื่อมต่อมาจากตัวแปรสภาพแวดล้อม เหตุผลอยู่ใน [การทดสอบโหลด](load-testing.md) |
| การ bind ของ gunicorn | `127.0.0.1:8000` หรือ Unix socket | ห้ามเปิด gunicorn สู่ภายนอกโดยตรง ให้อยู่หลัง Nginx เสมอ |
| การรีสตาร์ต worker | `HUP` เมื่อนำขึ้นใช้งาน (systemd `reload`) | ทำคำขอที่ค้างอยู่ให้เสร็จ แล้วแทนที่ worker ด้วยโค้ดใหม่ |
| การเชื่อมต่อฐานข้อมูล | เมื่อ `DB_POOL=true` จะมีพูลการเชื่อมต่อ psycopg ต่อ worker (`DB_POOL_MIN`, `DB_POOL_MAX`) | worker × `DB_POOL_MAX` + การเชื่อมต่อของ Celery ต้องต่ำกว่า `max_connections` ของ PostgreSQL การเชื่อมต่อที่คืนสู่พูลจะถูกล้างผู้ดำเนินการของเซสชันฐานข้อมูล (`ninefruits.core.pool.reset_connection`) |
| Nginx `client_max_body_size` | `32m` | ขีดจำกัดสูงสุดของการอัปโหลดเอกสารการรับสมัคร หลักฐานการสอบ และรูปถ่าย (เผื่อไว้เหนือการตรวจสอบ 5MB และ 2MB ของแอปพลิเคชัน) |
| ไฟล์สแตติกของ Nginx | `location /static/ { alias <repository>/staticfiles/; }` | Nginx ให้บริการผลลัพธ์ของ `collectstatic` เอง |
| ไฟล์ส่วนตัว | **ห้ามแมป** `PRIVATE_MEDIA_ROOT` (ค่าเริ่มต้น `storage/private`) ใน Nginx | รูปถ่าย เอกสารใบสมัคร และ PDF หนังสือรับรอง ดาวน์โหลดได้เฉพาะผ่าน view ที่ตรวจสอบสิทธิ์ |
| ส่วนหัวของ Nginx | `X-Forwarded-For $proxy_add_x_forwarded_for`, `X-Forwarded-Proto $scheme`, `Host $host` และ `X-Request-Id $request_id` (ไม่บังคับ) | ที่อยู่ของไคลเอนต์ การตรวจจับ HTTPS การติดตามรายคำขอ |
| Gotenberg, Redis, PostgreSQL | ที่อยู่ภายในเท่านั้น | ห้ามเปิดสู่ภายนอก |

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

### พร็อกซีและที่อยู่ของไคลเอนต์

ขีดจำกัดการเข้าสู่ระบบ ขีดจำกัดอัตราของ API และที่อยู่ IP ในบันทึกการตรวจสอบ ใช้ที่อยู่ของไคลเอนต์ที่กำหนดโดย `ninefruits.core.http.client_ip`

- `TRUSTED_PROXY_COUNT`: จำนวน reverse proxy หน้าแอปพลิเคชันที่ต่อท้าย `X-Forwarded-For` ใช้ `1` สำหรับ Nginx ตัวเดียว `2` สำหรับตัวกระจายโหลดร่วมกับ Nginx `0` (ค่าเริ่มต้น) ใช้ `REMOTE_ADDR` รายการที่อยู่ห่างจากด้านขวาเท่าจำนวนนี้คือที่อยู่ของไคลเอนต์ รายการที่อยู่ทางซ้ายถัดไป (ซึ่งไคลเอนต์ส่งมา) จะไม่ถูกเชื่อถือเลย
- **หากค่าต่ำกว่าจำนวนพร็อกซีจริง** ผู้ใช้ทุกคนจะดูเหมือนมาจากที่อยู่ของ Nginx และขีดจำกัดการเข้าสู่ระบบจะใช้กับทั้งมหาวิทยาลัยพร้อมกัน **หากค่าสูงกว่า** แอปพลิเคชันจะเชื่อถือ `X-Forwarded-For` ที่ไคลเอนต์ส่งมา และขีดจำกัดอาจถูกหลบเลี่ยงได้ หลังนำขึ้นใช้งาน ให้ตรวจสอบว่าที่อยู่ IP ใน **การตรวจสอบ > เหตุการณ์ด้านความปลอดภัย** ในแผงผู้ดูแลระบบเป็นที่อยู่จริงของผู้ใช้
- `LOGIN_RATE_LIMIT_PER_IP`: จำนวนครั้งที่พยายามเข้าสู่ระบบต่อที่อยู่ของไคลเอนต์ (django-allauth ค่าเริ่มต้น `30/m/ip`) ต้นฉบับไม่มีขีดจำกัดนี้ หากทั้งมหาวิทยาลัยออกอินเทอร์เน็ตผ่านที่อยู่ NAT เดียว ค่านี้จะต่ำเกินไปสำหรับเช้าวันแรกของการลงทะเบียนเรียน ให้เพิ่มขึ้น (เช่น `300/m/ip`) ค่าว่างหมายถึงไม่มีขีดจำกัดต่อที่อยู่ (เหมือนต้นฉบับ) ขีดจำกัดความล้มเหลวต่อบัญชี (5 ครั้งต่อนาที) และการล็อกบัญชีมีผลโดยไม่ขึ้นกับค่านี้

## ตัวแปรสภาพแวดล้อม

`.env.example` มีค่าเริ่มต้นสำหรับการพัฒนา ในระบบใช้งานจริง ให้ฉีดข้อมูลลับจากที่จัดเก็บข้อมูลลับ

| ตัวแปร | ค่าในระบบใช้งานจริง | หมายเหตุ |
|---|---|---|
| `DJANGO_ENV` | `production` | ปฏิเสธ `setup_demo` และนำป้ายสภาพแวดล้อมออกจากแผงผู้ดูแลระบบ |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` | `DEBUG=False`, `SECURE_SSL_REDIRECT`, `SECURE_PROXY_SSL_HEADER`, HSTS คุกกี้ที่ปลอดภัย |
| `DJANGO_DEBUG` | `false` | |
| `DJANGO_SECRET_KEY` | ที่จัดเก็บข้อมูลลับ | [การจัดการคีย์](security-keys.md) เมื่อเปลี่ยนคีย์ คีย์เดิมจะไปอยู่ใน `DJANGO_SECRET_KEY_FALLBACKS` |
| `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | `sis.example.ac.kr`, `https://sis.example.ac.kr` | รายการคั่นด้วยจุลภาค |
| `APP_URL` | `https://sis.example.ac.kr` | ลิงก์ในอีเมล QR code ตรวจสอบหนังสือรับรอง |
| `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, `PII_PREVIOUS_KEYS` | ที่จัดเก็บข้อมูลลับ | หากสูญหาย จะถอดรหัสข้อมูลส่วนบุคคลไม่ได้ |
| `DB_HOST`, `DB_PORT`, `DB_DATABASE` | | |
| `DB_USERNAME`, `DB_PASSWORD` | `app_runtime` | แอปพลิเคชันและ Celery |
| `DB_MIGRATOR_USERNAME`, `DB_MIGRATOR_PASSWORD` | `app_migrator` | ใช้โดย `migrate`, `setup_install`, `audit_seal` และ `audit_prune` เก็บรหัสผ่านไว้เฉพาะบนเซิร์ฟเวอร์ที่รันการนำขึ้นใช้งานและเซิร์ฟเวอร์ที่รันการผนึกบันทึกการตรวจสอบ (`audit_seal`) |
| `GUNICORN_BIND`, `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT`, `GUNICORN_MAX_REQUESTS`, `GUNICORN_FORWARDED_ALLOW_IPS` | `127.0.0.1:8000` ค่าจาก [การทดสอบโหลด](load-testing.md), `60`, `2000`, `127.0.0.1` | อ่านโดย `config/gunicorn.py` จำนวน worker เริ่มต้นคือ 2 ต่อคอร์ CPU + 1 `GUNICORN_FORWARDED_ALLOW_IPS` บอกเพียงว่า gunicorn เชื่อถือ `X-Forwarded-Proto` ของผู้ใด ที่อยู่ของไคลเอนต์มาจาก `TRUSTED_PROXY_COUNT` |
| `DB_POOL`, `DB_POOL_MIN`, `DB_POOL_MAX`, `DB_PREPARE_THRESHOLD` | ค่าที่กำหนดใน [การทดสอบโหลด](load-testing.md): `true`, `1`, `2`, `2` | `DB_PREPARE_THRESHOLD` เปิดใช้ prepared statement (ลดต้นทุนการวางแผนคิวรีของ RLS) 0 คือปิด |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis ภายใน | broker และผลลัพธ์ใช้ `REDIS_URL` เป็นค่าเริ่มต้น |
| `MAIL_BACKEND`, `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_ENCRYPTION` (`starttls`/`ssl`), `DEFAULT_FROM_EMAIL` | SMTP relay ของมหาวิทยาลัย | คำเชิญ รหัสยืนยันตัวตนแบบสองขั้นตอน การแจ้งเตือนการลงทะเบียนเรียนและผลการเรียน |
| `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` | ที่อยู่ภายใน, `60` | |
| `PRIVATE_MEDIA_ROOT` | ดิสก์ที่มีการสำรองข้อมูล | ที่จัดเก็บไฟล์ส่วนตัว |
| `TRUSTED_PROXY_COUNT` | โดยทั่วไป `1` | หัวข้อข้างต้น |
| `LOGIN_RATE_LIMIT_PER_IP` | `30/m/ip` หรือสูงกว่า | หัวข้อข้างต้น |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | `true`, `31536000` | เมื่อเปิดใช้ HTTPS ครั้งแรก ให้ลอง HSTS ระยะสั้น (`300`) ก่อนเพิ่มค่า |
| `SESSION_LIFETIME_MINUTES` | `120` | อายุของเซสชันที่เข้าสู่ระบบ |
| `APP_TIMEZONE`, `INSTITUTION_TIMEZONE` | `UTC` เขตเวลาของสถาบัน | เวลาของเซิร์ฟเวอร์และงานตามกำหนดเวลาเป็น UTC หน้าจอใช้เขตเวลาของสถาบัน |
| `API_THROTTLE_ANON`, `API_THROTTLE_USER`, `API_THROTTLE_INTEGRATION`, `API_TOKEN_TTL_DAYS` | ค่าเริ่มต้น | [คู่มือการเชื่อมต่อ LMS](../../../lms-integration-guide.md) |
| `LOG_LEVEL` | `INFO` | ล็อกออกไปยัง standard output เป็นออบเจ็กต์ JSON หนึ่งรายการต่อบรรทัด |
| `VITE_DEV_MODE` | `false` | ระบบใช้งานจริงใช้ผลลัพธ์จากการ build (`static/dist/manifest.json`) |

## ขั้นตอนการนำขึ้นใช้งาน

1. สำรองข้อมูล ([การสำรองและกู้คืนข้อมูล](backup-restore.md)) และรัน `uv run manage.py audit_verify_chain`
2. นำโค้ดขึ้นใช้งาน: `git pull` (หรืออิมเมจใหม่), `uv sync --frozen --no-dev`, `npm ci && npm run build`
3. `uv run manage.py setup_install --force`: ไมเกรชัน (สลับไปใช้การเชื่อมต่อ `app_migrator` โดยอัตโนมัติ) ปรับปรุงข้อมูลพื้นฐานที่จำเป็น (การแก้ไขของผู้ดูแลระบบจะคงอยู่) ซิงค์แคตตาล็อกสิทธิ์ เมื่อรันไมเกรชันแยกต่างหาก `uv run manage.py migrate` ก็ใช้ `app_migrator` โดยอัตโนมัติเช่นกัน ไม่มีทางรัน DDL ด้วย `app_runtime`
4. `uv run manage.py compilemessages --ignore=.venv`, `uv run manage.py collectstatic --noinput` อิมเมจ Docker สำหรับระบบใช้งานจริงรันทั้งสองคำสั่งตอน build
5. รีสตาร์ตโพรเซส: gunicorn `reload` (HUP) worker ของ Celery (TERM ให้งานที่กำลังทำเสร็จก่อน ด้วย `acks_late` งานที่ถูกขัดจังหวะจะทำงานอีกครั้ง) Celery beat ให้รัน **beat เพียงโพรเซสเดียว** ในทุกเซิร์ฟเวอร์รวมกัน หากมีสองโพรเซส งานตามกำหนดเวลาทุกงานจะเข้าคิวสองครั้ง (ล็อก Redis ของแต่ละงานป้องกันการทำงานพร้อมกัน ไม่ได้ป้องกันการเข้าคิวซ้ำ)
6. ตรวจสอบ: `uv run manage.py check --deploy`, `uv run manage.py system_health_check` (รหัสสิ้นสุดการทำงาน 0), `GET /api/v1/health/` (`ok`) การเข้าสู่ระบบแผงผู้ดูแลระบบ `uv run manage.py pdf_sample` ตรวจสอบใน Flower ว่า worker เชื่อมต่ออยู่

## การตรวจสอบตามรอบ

| ความถี่ | งาน |
|---|---|
| รายวัน (อัตโนมัติ) | `audit.seal`, `lms.reconcile` การปล่อยที่นั่งสำรองของการลงทะเบียน การเลื่อนจากรายชื่อสำรอง การหมดอายุของใบสมัครฉบับร่าง ([งานตามกำหนดเวลา](scheduled-jobs.md)) |
| รายสัปดาห์ | `/api/v1/health/` และ `check --deploy` การอัปเดตความปลอดภัยของ Python, OS และ dependency (`pip-audit`) งานที่ล้มเหลวใน Flower |
| รายเดือน | `media_prune_orphans --dry-run` การซ้อมกู้คืนข้อมูลสำรอง `audit_verify_chain` |
| ทุกภาคการศึกษา | ทบทวนการกำหนดบทบาท (ผู้ที่ลาออกหรือย้าย) ลบบันทึกการตรวจสอบที่เลยระยะเวลาเก็บรักษา (`audit_prune`) ก่อนการลงทะเบียนเรียน ให้ตรวจสอบ `LOGIN_RATE_LIMIT_PER_IP` และจำนวน worker อีกครั้ง |
