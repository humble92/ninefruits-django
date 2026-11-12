# คู่มือระบบสารสนเทศนักศึกษา (ภาษาไทย)

สำหรับเจ้าหน้าที่ที่ดูแลระบบในการปฏิบัติงานประจำวัน และสำหรับผู้ดูแลระบบไอทีที่ติดตั้ง นำขึ้นใช้งาน และบำรุงรักษาระบบ หน้าจอของระบบมีให้ใช้เป็นภาษาไทย (เมนูภาษา)

ภาษาอื่น: [English](../en/README.md), [한국어](../ko/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md), [Deutsch](../de/README.md), [Filipino](../fil/README.md), [Français](../fr/README.md), [日本語](../ja/README.md), [Монгол](../mn/README.md), [Bahasa Melayu](../ms/README.md), [नेपाली](../ne/README.md), [Русский](../ru/README.md), [Türkçe](../tr/README.md), [Oʻzbek](../uz/README.md), [Tiếng Việt](../vi/README.md) ฉบับภาษาเกาหลีเป็นต้นฉบับ ฉบับภาษาอื่นเป็นงานแปลที่ยังรอการตรวจทานโดยเจ้าของภาษา

## คู่มือผู้ดูแลระบบ

[admin/README.md](admin/README.md) — บทที่ 1 ถึง 28 ตั้งแต่การเริ่มต้นใช้งาน ผู้ใช้และบทบาท ไปจนถึงการตั้งค่าสถาบัน การรับสมัคร การลงทะเบียนเรียน ผลการเรียน หนังสือรับรอง การสำเร็จการศึกษา และการเชื่อมต่อ LMS

## การดูแลระบบ

| ไฟล์ | เนื้อหา |
|---|---|
| [installation.md](operations/installation.md) | ข้อกำหนดของระบบ บทบาทของฐานข้อมูล การตั้งค่าสภาพแวดล้อม การติดตั้งครั้งแรกและการอัปเดต |
| [deployment-checklist.md](operations/deployment-checklist.md) | การตั้งค่า Python และ gunicorn ตัวแปรสภาพแวดล้อมสำหรับระบบใช้งานจริง ขั้นตอนการนำขึ้นใช้งาน การตรวจสอบตามรอบ |
| [commands.md](operations/commands.md) | ข้อมูลอ้างอิงของคำสั่งจัดการ (management command) ทุกคำสั่ง (`uv run manage.py ...`): ตัวเลือก บันทึกการตรวจสอบ รหัสสิ้นสุดการทำงาน ตัวอย่าง |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | โพรเซสที่ทำงานต่อเนื่อง (Celery worker, beat) งานตามกำหนดเวลาและงานในคิว วิธีตรวจพบความล้มเหลว (Flower) |
| [backup-restore.md](operations/backup-restore.md) | สิ่งที่ต้องสำรอง ตัวอย่างการ dump และการกู้คืน การซ้อมกู้คืน |
| [security-keys.md](operations/security-keys.md) | คีย์ลับสามชุด วิธีจัดเก็บ การเปลี่ยนคีย์ข้อมูลส่วนบุคคล |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | ห่วงโซ่แฮชของบันทึกการตรวจสอบ ระยะเวลาเก็บรักษาและการลบ การล้างไฟล์ การตรวจสุขภาพระบบ |
| [load-testing.md](operations/load-testing.md) | การทดสอบโหลดสำหรับช่วงลงทะเบียนเรียนหนาแน่น (Locust) และการตัดสินใจเรื่องจำนวน worker |
| [troubleshooting.md](operations/troubleshooting.md) | อาการที่พบบ่อย สิ่งที่ต้องตรวจสอบ การติดตามรายคำขอ |

## เอกสารอื่น

- [คู่มือการเชื่อมต่อ LMS](../../lms-integration-guide.md): API และตัวเชื่อมต่อ LMS (สำหรับนักพัฒนา)
- [การเพิ่มภาษา](../../development/adding-a-language.md), [กฎการตั้งชื่อ](../../development/naming.md), [รายการตรวจทาน](../../development/review-checklist.md) (สำหรับนักพัฒนา)
- [สารบัญเอกสาร](../../README.md)
