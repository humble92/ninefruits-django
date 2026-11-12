# การสำรองและกู้คืนข้อมูล

- ผู้อ่าน: ผู้ดูแลระบบไอที
- เกี่ยวข้อง: [การติดตั้ง](installation.md), [การจัดการคีย์](security-keys.md), [ความครบถ้วนของบันทึกการตรวจสอบ](audit-and-maintenance.md)

## สิ่งที่ต้องสำรอง

| เป้าหมาย | วิธีการ | ความถี่ (แนะนำ) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` หรือ PITR (การเก็บ WAL) | สำรองเต็มรายวัน + WAL ต่อเนื่อง |
| ที่จัดเก็บไฟล์ส่วนตัว (`PRIVATE_MEDIA_ROOT` ค่าเริ่มต้น `storage/private`) | สแนปช็อต หรือบักเก็ตที่เปิดการจัดเก็บหลายเวอร์ชัน | เช่นเดียวกับฐานข้อมูล |
| การตั้งค่าสภาพแวดล้อมและคีย์ (`DJANGO_SECRET_KEY`, `PII_*` รหัสผ่านฐานข้อมูล) | ที่จัดเก็บข้อมูลลับ | ทุกครั้งที่มีการเปลี่ยนแปลง |

ฐานข้อมูลและที่จัดเก็บไฟล์ต้องกู้คืนได้ ณ จุดเวลาเดียวกัน (เมทาดาทาของรูปถ่าย เอกสารประกอบใบสมัคร PDF หนังสือรับรอง และหลักฐานการสอบอยู่ในตาราง `media` ของฐานข้อมูล) ไม่ต้องสำรอง Redis เพราะเก็บเพียงแคช ล็อก และคิว ส่วนเซสชันก็จัดเก็บในฐานข้อมูลด้วย (`django_session`) รายการงานตามกำหนดเวลา (django-celery-beat) อยู่ในฐานข้อมูลเช่นกัน และ beat จะปรับให้ตรงกับ `config/celery.py` เมื่อเริ่มทำงาน

`staticfiles/` และ `static/dist/` เป็นผลลัพธ์จากการ build และไม่ต้องสำรอง (`npm run build` และ `collectstatic` จะสร้างขึ้นใหม่)

## ตัวอย่างการสำรองฐานข้อมูล

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` เป็นเจ้าของทุกสคีมา (`public`, `audit`, `reporting`, `util`) จึงต้องสำรองด้วยบัญชีนี้ บทบาท (`app_*`) เป็นออบเจ็กต์ระดับคลัสเตอร์และไม่รวมอยู่ใน dump บนเซิร์ฟเวอร์ที่จะกู้คืน ให้สร้างบทบาทก่อนตามที่อธิบายใน [การติดตั้ง](installation.md) หัวข้อที่ 2

หากรัน `uv run manage.py audit_verify_chain` ก่อนสำรอง คำสั่งเดียวกันบนฐานข้อมูลที่กู้คืนจะช่วยให้เปรียบเทียบห่วงโซ่บันทึกการตรวจสอบได้

## ตัวอย่างการกู้คืน

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

หากต้องการรันแอปพลิเคชันบนฐานข้อมูลที่กู้คืน ให้ตั้งค่า `DB_DATABASE=ninefruits_restore` และ **คีย์ ณ เวลาที่สำรอง** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY` และ `PII_PREVIOUS_KEYS` หากมีการเปลี่ยนคีย์หลังจากนั้น) จากนั้นตรวจสอบสถานะ:

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

หาก `migrate --check` รายงานว่ามีไมเกรชันที่ต้องนำไปใช้ แสดงว่าข้อมูลสำรองเก่ากว่าโค้ดปัจจุบัน ให้กู้คืนด้วยโค้ดเวอร์ชันเดียวกัน หรืออัปเกรดด้วย `setup_install --force`

## การซ้อมกู้คืน

ทุกไตรมาส ให้กู้คืนไปยังเซิร์ฟเวอร์แยกต่างหากและตรวจสอบ: การเข้าสู่ระบบ การถอดรหัสข้อมูลส่วนบุคคล (**แสดงเลขประจำตัวประชาชน** ของบุคคลในแผงผู้ดูแลระบบ คีย์ตรงกัน) การดูบันทึกการตรวจสอบและ `audit_verify_chain` การเปิดไฟล์ (รูปถ่าย PDF หนังสือรับรอง) หน้าตรวจสอบหนังสือรับรอง บันทึกผลการซ้อม (เวลาที่ใช้ ปัญหาที่พบ)
