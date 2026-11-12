# งานตามกำหนดเวลาและคิว

- ผู้อ่าน: ผู้ดูแลระบบไอที
- เกี่ยวข้อง: [รายการตรวจสอบการนำขึ้นใช้งาน](deployment-checklist.md), [ความถูกต้องของบันทึกการตรวจสอบ](audit-and-maintenance.md), [คู่มือคำสั่ง](commands.md)

## โพรเซสที่ทำงานต่อเนื่อง

| โพรเซส | คำสั่ง | การตรวจสอบ |
|---|---|---|
| เว็บ | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| ตัวประมวลผลคิว (worker) | `uv run celery -A config worker --loglevel=INFO` | **Workers** ใน Flower, `uv run celery -A config inspect ping` |
| ตัวจัดกำหนดเวลา | `uv run celery -A config beat --loglevel=INFO` (**มีเพียงโพรเซสเดียวทั้งระบบ**) | `scheduler` ใน `/api/v1/health/` ล็อกของ beat |
| ตัวติดตามคิว (ไม่บังคับ) | `uv run celery -A config flower --port=5555` | เฉพาะในเครือข่ายภายใน หรือหลังการจำกัดการเข้าถึงของ Nginx |

ทั้งสามใช้โค้ดและตัวแปรสภาพแวดล้อมเดียวกัน ตัวอย่าง systemd:

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

สร้างบริการรูปแบบเดียวกันอีกหนึ่งบริการสำหรับ beat ด้วย `ExecStart=... celery -A config beat --loglevel=INFO` แม้จะมีหลายเซิร์ฟเวอร์ ให้เปิดใช้บริการ beat บนเซิร์ฟเวอร์เดียวเท่านั้น

## งานตามกำหนดเวลา

การลงทะเบียนงานคือ `beat_schedule` ใน `config/celery.py` เมื่อ beat เริ่มทำงานจะปรับตัวจัดกำหนดเวลาแบบฐานข้อมูลของ django-celery-beat (ตาราง `django_celery_beat_*`) ให้ตรงกัน เวลาเป็นเขตเวลาของเซิร์ฟเวอร์ (`APP_TIMEZONE` ค่าเริ่มต้น UTC) งานตามกำหนดเวลาทุกงานถือล็อก Redis (`single_instance`) งานเดียวกันจึงไม่ทำงานซ้อนกันสองครั้ง

| งาน (ชื่อใน Celery) | ความถี่ | คำสั่งที่ทำงานเดียวกัน | การตรวจพบความล้มเหลว |
|---|---|---|---|
| `admission.expire_drafts` | ทุกวันเวลา 03:10 | `admission_expire_drafts` | รันคำสั่งนั้นโดยตรง ทุกครั้งที่รันจึงถูกบันทึกในบันทึกการดำเนินงาน (log `command`) หากไม่มีบันทึกเกินหนึ่งวัน ให้ตรวจสอบ beat และ worker |
| `registration.release_reserved_seats` | ทุก 5 นาที | `registration_release_reserved_seats` | ไม่มีบันทึกการตรวจสอบ หากการจัดสรรที่นั่งที่เลยเวลาปล่อยแล้วยังมี `release_processed_at` ว่างอยู่ ให้ตรวจสอบ beat |
| `registration.promote_waitlists` | ทุกชั่วโมง ตรงต้นชั่วโมง | `waitlist_promote` | ไม่มีรายการในบันทึกการดำเนินงาน (การลงทะเบียนที่เลื่อนขึ้นปรากฏในการเปลี่ยนแปลงข้อมูลเป็น `system:task:registration.promote_waitlists`) ผลของงานใน Flower (กลุ่มเรียน การเลื่อนขึ้น) |
| `lms.reconcile` | ทุกวันเวลา 02:30 | `lms_reconcile` | บันทึกการซิงค์ต่อการเชื่อมโยง (แผงผู้ดูแลระบบ **การเชื่อมต่อ LMS**) ผลของงานใน Flower |
| `audit.seal` | ทุกวันเวลา 03:30 | `audit_seal` | ผนึกห่วงโซ่แฮชของบันทึกการตรวจสอบ ([ความถูกต้องของบันทึกการตรวจสอบ](audit-and-maintenance.md)) ตรวจสอบหาก `audit_verify_chain` แสดงแถวที่ยังไม่ผนึกมากกว่าปริมาณของหนึ่งวัน |
| `core.heartbeat` | ทุกนาที | ไม่มี | เขียนเวลาที่รันล่าสุดลงในคีย์แคช `system:heartbeat` `/api/v1/health/` จะตอบ `degraded` เมื่อเก่ากว่า 5 นาที |

## งานในคิว

| งาน (ชื่อใน Celery) | สิ่งที่เรียกใช้ | หมายเหตุ |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | หนึ่งงานต่อชุดระเบียน (group) หากชุดใดล้มเหลว ให้รันคำสั่งอีกครั้ง (ระเบียนที่ใช้คีย์ปัจจุบันแล้วจะถูกข้าม) |
| `registration.promote_waitlist` | การลดหรือถอนรายวิชา การปล่อยที่นั่งที่จัดสรรไว้ | ทำงานได้เพียงหนึ่งงานต่อกลุ่มเรียน (ล็อก Redis ป้องกันการซ้ำ) การเลื่อนจากรายชื่อสำรองจะตรวจสอบกฎการลงทะเบียนทุกข้ออีกครั้ง เข้าคิวหลังทรานแซกชันยืนยันแล้ว |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close` การปิดภาคการศึกษาในแผงผู้ดูแลระบบ | chord: งานครั้งละ 100 คน แล้วตามด้วยงานปิดท้าย (การจัดอันดับเกียรตินิยม การเปลี่ยนสถานะภาคการศึกษา การแจ้งเจ้าหน้าที่ผู้เริ่ม) ความคืบหน้าคือแถว `job_batches` `term-close:{term code}` ซึ่งแสดงในแผงผู้ดูแลระบบ งานของแต่ละชุดจะลองใหม่ได้สูงสุด 3 ครั้งเมื่อเกิดข้อผิดพลาดของฐานข้อมูล หากยังล้มเหลว ทั้งชุดจะถูกทำเครื่องหมายว่าล้มเหลวและงานปิดท้ายจะไม่ทำงาน ให้แก้ไขสาเหตุ แล้วเริ่มการปิดภาคการศึกษาอีกครั้ง (การคำนวณรายนักศึกษาให้ผลเหมือนเดิมเมื่อรันซ้ำ) |
| `importing.import_chunk` | การนำเข้า CSV ในแผงผู้ดูแลระบบ, `reference_import` | หนึ่งงานต่อหนึ่งส่วน ผลลัพธ์อยู่ใน `imports` แถวที่ล้มเหลวอยู่ใน `failed_import_rows` (ผลการนำเข้าในแผงผู้ดูแลระบบ) |
| `lms.sync_section`, `lms.sync_enrollment` | เหตุการณ์การเปลี่ยนแปลงกลุ่มเรียนและการลงทะเบียน | เมื่อล้มเหลวจะลองใหม่ได้สูงสุด 3 ครั้ง ห่างกันหนึ่งนาที `lms.reconcile` ทุกคืนจะแก้ไขส่วนที่เหลือ |

ขณะงานทำงาน ผู้ดำเนินการในฐานข้อมูลจะถูกบันทึกเป็น `system:task:{task name}` (เช่น `system:task:grading.close_term_records`) พร้อมรหัสคำขอและผู้ใช้ของคำขอที่นำงานเข้าคิว

Flower แสดงงานที่ล้มเหลว (**Tasks** สถานะ `FAILURE`) และข้อยกเว้นของงาน งาน Celery ใช้ `acks_late` งานที่ถูกขัดจังหวะเพราะ worker หยุดทำงานจึงจะทำงานอีกครั้ง ทุกงานออกแบบให้ได้ผลเหมือนเดิมเมื่อรันซ้ำ (idempotent)
