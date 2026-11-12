# 9. การนำเข้า CSV

ใช้ปุ่ม **นำเข้า CSV** ที่ด้านบนของหน้าจอหน่วยงาน หลักสูตร อาคาร ห้อง และรายการรหัส (สิทธิ์ `นำเข้าข้อมูลอ้างอิงจาก CSV`) ระเบียนนักศึกษา อาจารย์ รายวิชา และการระงับการลงทะเบียนนำเข้าในลักษณะเดียวกัน (ดูด้านล่าง) ไฟล์ขนาดใหญ่มากสามารถให้ผู้ดูแลด้าน IT นำเข้าในลักษณะเดียวกันด้วยคำสั่ง `reference_import`

## กฎทั่วไป

- บรรทัดแรกเป็นชื่อคอลัมน์ (ตามตารางด้านล่าง) การเข้ารหัสอักขระเป็น UTF-8 หากใช้ Excel ให้บันทึกเป็น "CSV UTF-8"
- แถวที่มีรหัสอยู่แล้วจะ **ปรับปรุง** รายการนั้น การนำเข้าไฟล์เดิมซ้ำจะไม่สร้างข้อมูลซ้ำ
- คอลัมน์ตามภาษาใช้รูปแบบ `คอลัมน์_ภาษา`: `name_en`, `name_ko`, `name_zh-hans` แถวใหม่ต้องมีชื่อภาษาอังกฤษ (`name_en`) เซลล์ว่างจะไม่ลบคำแปลที่มีอยู่
- วันที่เขียนเป็น `2026-03-01` ค่าใช่/ไม่ใช่เขียนเป็น `1`/`0` หรือ `true`/`false`
- ระบบตรวจสอบแถวหัวตารางก่อน (หากไม่มีคอลัมน์ที่จำเป็น จะไม่นำเข้าข้อมูลใดเลย) ไฟล์ที่มีไม่เกิน 500 แถวจะนำเข้าทันที ไฟล์ที่ใหญ่กว่านั้นจะประมวลผลเบื้องหลัง (Celery) ผลลัพธ์จะแสดงในหน้าการนำเข้าที่ **ข้อมูลอ้างอิง > ประวัติการนำเข้า CSV** (จำนวนแถวที่นำเข้า แถวที่ล้มเหลวและเหตุผล) หากมีแถวที่ล้มเหลว **ดาวน์โหลดแถวที่ล้มเหลว** จะให้ไฟล์ CSV พร้อมเหตุผลของแต่ละแถว แก้ไขแล้วนำเข้าเฉพาะไฟล์นั้นอีกครั้ง
- ชื่อคอลัมน์ต้องตรงกับตารางด้านล่าง คอลัมน์ที่ไม่รู้จักจะถูกละเว้น ชื่อคอลัมน์ `name_zh_CN` ของระบบเดิมจะยอมรับเป็น `name_zh-hans`

## รูปแบบคอลัมน์

| ประเภท | คอลัมน์ที่ต้องมี | คอลัมน์ที่ไม่บังคับ |
|---|---|---|
| หน่วยงาน | `code`, `type` (รหัสประเภทหน่วยงาน), `name_en`, `effective_start_date` | `parent` (รหัสหน่วยงานต้นสังกัด), `name_ko` ฯลฯ, `short_name_*`, `effective_end_date`, `sort_order` |
| หลักสูตร | `code`, `org_unit` (รหัสหน่วยงาน), `degree_level`, `name_en`, `effective_start_date` | `degree_title_*`, `standard_duration_years`, `effective_end_date`, `allows_second_major`, `allows_minor` |
| อาคาร | `code`, `name_en` | `name_*`, `address`, `is_active` |
| ห้อง | `building` (รหัสอาคาร), `code` (หมายเลขห้อง) | `name_*`, `room_type` (รหัสประเภทห้อง), `org_unit`, `capacity`, `is_schedulable`, `is_active` |
| ค่ารหัส | `type` (รหัสรายการ), `code`, `name_en` | `name_*`, `sort_order`, `is_active` |

ค่าของ `degree_level`: `associate`, `bachelor`, `master`, `doctorate`, `certificate`, `non_degree`

สำหรับหน่วยงาน หน่วยงานต้นสังกัดต้องมาก่อน (เรียงเป็น มหาวิทยาลัย → คณะ → ภาควิชา)

## ตัวอย่าง: หน่วยงาน

```csv
code,type,parent,name_en,name_ko,effective_start_date
UNI,university,,Sample University,샘플대학교,1990-03-01
ENG,college,UNI,College of Engineering,공과대학,1990-03-01
CSE,department,ENG,Computer Science,컴퓨터공학과,1995-03-01
```

## นักศึกษาและอาจารย์

ระเบียนนักศึกษาจับคู่และปรับปรุงด้วย `student_number` อาจารย์ด้วย `employee_number` ทั้งสองประเภทใช้คอลัมน์ข้อมูลบุคคลร่วมกัน

| ประเภท | คอลัมน์ที่ต้องมีสำหรับแถวใหม่ | คอลัมน์ที่ไม่บังคับ |
|---|---|---|
| ระเบียนนักศึกษา | `student_number`, `program` (รหัสหลักสูตร), `admission_date`, `family_name` | `catalog_year` (หากว่างใช้ปีที่เข้าศึกษา), `year_level`, `status`, `graduation_date`, `institutional_email` |
| อาจารย์ | `employee_number`, `org_unit` (รหัสหน่วยงาน), `employment_type`, `family_name` | `academic_title_*`, `hire_date`, `end_date` |
| คอลัมน์ข้อมูลบุคคล (ใช้ร่วมกัน) | — | `given_name`, ชื่อตามภาษา เช่น `name_ko`, `birth_date`, `gender`, `email`, `phone`, `national_id` |

- ค่าของ `status`: `enrolled`, `on_leave`, `withdrawn`, `dismissed`, `graduated` (สำหรับ graduated ต้องมี `graduation_date`) สถานภาพที่เปลี่ยนโดยการนำเข้าถือเป็น **การแก้ไขข้อมูล** และไม่สร้างประวัติการเปลี่ยนสถานภาพ การเปลี่ยนแปลงจริงให้บันทึกบนหน้าจอ ([บทที่ 13](13-status-changes-and-advisors.md))
- ค่าของ `employment_type`: `full_time`, `part_time`, `adjunct`, `visiting`, `emeritus` ค่าของ `gender`: `female`, `male`, `other`, `undisclosed`
- หาก `national_id` ของระเบียนนักศึกษาใหม่ตรงกับบุคคลที่มีอยู่ ระเบียนจะผูกกับบุคคลนั้น (คืนสภาพนักศึกษา) มิฉะนั้นจะสร้างบุคคลใหม่ เมื่อปรับปรุง เซลล์ว่างจะไม่ลบค่าที่มีอยู่
- นักศึกษาและอาจารย์ที่นำเข้าจะยังไม่มีบัญชี ให้ส่งคำเชิญด้วย [การเชิญให้สร้างบัญชี](14-merge-and-invitations.md#การเชิญให้สร้างบัญชี)

```csv
student_number,program,admission_date,year_level,status,family_name,given_name,name_ko,birth_date
202600001,B-CSE,2026-03-02,1,enrolled,Kim,Minsu,김민수,2007-05-01
```

การนำเข้าฉบับรายวิชาอธิบายไว้ใน [บทที่ 17](17-courses-and-curriculum.md) การนำเข้าการระงับการลงทะเบียนอธิบายไว้ใน [บทที่ 20](20-registration.md)

## การระงับการลงทะเบียน

**นำเข้า CSV** ที่ด้านบนของรายการ **การลงทะเบียนเรียน > การระงับ** (สิทธิ์ `ระงับและยกเลิกการระงับ ให้การอนุญาตพิเศษตามกฎ`) หรือ `uv run manage.py reference_import registration_holds` ใช้โหลดข้อมูล `SRDENY` ของระบบเดิม หรือรายชื่อนักศึกษาที่ค้างชำระจากฝ่ายการเงิน

| คอลัมน์ที่ต้องมี | คอลัมน์ที่ไม่บังคับ |
|---|---|
| `student_number`, `hold_type` (`unregistered`, `financial`, `academic`, `administrative`, `other`), `reason` | `starts_at` (ค่าเริ่มต้น: เวลาที่นำเข้า), `ends_at`, `blocks_registration` (ค่าเริ่มต้น 1), `blocks_grades`, `blocks_certificates` |

- ทุกแถวจะสร้างการระงับใหม่ (แหล่งที่มา `import`) การนำเข้าไฟล์เดิมสองครั้งจะสร้างการระงับซ้ำสองครั้ง จึงควรตรวจสอบรายการก่อนนำเข้าอีกครั้ง
- แถวที่มีรหัสนักศึกษาที่ไม่รู้จักจะไม่สำเร็จ การยกเลิกการระงับทำบนหน้าจอพร้อมระบุเหตุผล ([บทที่ 20](20-registration.md))
- เวลาเขียนเป็น `2027-03-15` หรือ `2027-03-15 09:00` (หากไม่ระบุเขตเวลาจะใช้เขตเวลาของเซิร์ฟเวอร์ คือ UTC) `ends_at` ต้องอยู่หลัง `starts_at`

```csv
student_number,hold_type,reason,ends_at
202312345,financial,Tuition unpaid 2027-1,
202254321,academic,Probation meeting needed,2027-03-15
```
