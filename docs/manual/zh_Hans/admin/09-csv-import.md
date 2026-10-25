# 9. CSV 导入

使用组织单位、专业项目、楼宇、教室、代码数据列表界面上方的 **导入 CSV** 按钮（`通过 CSV 导入基础数据` 权限）。学籍、教师、课程、选课限制也以同样方式导入（见下文）。特别大的文件可由 IT 运维人员用 `reference_import` 命令以同样方式导入。

## 通用规则

- 第一行是列名（见下表）。编码为 UTF-8。在 Excel 中以"CSV UTF-8"格式保存。
- 已存在相同代码的行时会 **更新**。同一文件重复导入也不会产生重复。
- 按语言区分的列采用 `列名_语言` 格式：`name_en`、`name_ko`、`name_zh-hans`。新行必须有英文名称（`name_en`）。空白单元格不会删除已有翻译。
- 日期写成 `2026-03-01`，是/否写成 `1`/`0` 或 `true`/`false`。
- 上传文件后先检查表头（缺少必填列时不导入任何内容）。500 行以内的文件立即导入，更大的文件在后台（Celery）处理。结果显示在 **基础数据 > CSV 导入** 的导入界面（已导入行数、失败的行及原因）。如有失败的行，可通过 **下载失败的行** 获取附带原因的 CSV。修正后只需重新导入该文件即可。
- 列名必须与下表一致，未知的列会被忽略。原系统的 `name_zh_CN` 列名也会按 `name_zh-hans` 接受。

## 列格式

| 种类 | 必填列 | 可选列 |
|---|---|---|
| 组织单位 | `code`、`type`（组织单位类型代码）、`name_en`、`effective_start_date` | `parent`（上级代码）、`name_ko` 等、`short_name_*`、`effective_end_date`、`sort_order` |
| 专业项目 | `code`、`org_unit`（单位代码）、`degree_level`、`name_en`、`effective_start_date` | `degree_title_*`、`standard_duration_years`、`effective_end_date`、`allows_second_major`、`allows_minor` |
| 楼宇 | `code`、`name_en` | `name_*`、`address`、`is_active` |
| 教室 | `building`（楼宇代码）、`code`（房间号） | `name_*`、`room_type`（用途代码）、`org_unit`、`capacity`、`is_schedulable`、`is_active` |
| 代码值 | `type`（列表代码）、`code`、`name_en` | `name_*`、`sort_order`、`is_active` |

`degree_level` 的值：`associate`、`bachelor`、`master`、`doctorate`、`certificate`、`non_degree`

组织单位的上级单位必须排在前面（按大学 → 学院 → 系的顺序排列）。

## 示例：组织单位

```csv
code,type,parent,name_en,name_ko,effective_start_date
UNI,university,,Sample University,샘플대학교,1990-03-01
ENG,college,UNI,College of Engineering,공과대학,1990-03-01
CSE,department,ENG,Computer Science,컴퓨터공학과,1995-03-01
```

## 学生与教师

学籍按 `student_number`（学号）、教师按 `employee_number`（工号）查找并更新已有行。两种类型都同时使用人员列。

| 种类 | 新行必填列 | 可选列 |
|---|---|---|
| 学籍 | `student_number`、`program`（专业项目代码）、`admission_date`、`family_name` | `catalog_year`（为空时取入学年份）、`year_level`、`status`、`graduation_date`、`institutional_email` |
| 教师 | `employee_number`、`org_unit`（单位代码）、`employment_type`、`family_name` | `academic_title_*`、`hire_date`、`end_date` |
| 人员列（通用） | — | `given_name`、`name_ko` 等各语言姓名、`birth_date`、`gender`、`email`、`phone`、`national_id` |

- `status` 的值：`enrolled`、`on_leave`、`withdrawn`、`dismissed`、`graduated`（为毕业时 `graduation_date` 必填）。通过导入更改的状态视为 **资料更正**，不会生成学籍异动历史。实际的异动在界面上办理（[第 13 章](13-status-changes-and-advisors.md)）。
- `employment_type` 的值：`full_time`、`part_time`、`adjunct`、`visiting`、`emeritus`。`gender` 的值：`female`、`male`、`other`、`undisclosed`。
- 新学籍的 `national_id` 与已有人员相同时，学籍会挂到该人员名下（重新入学）。否则创建新人员。更新时空白单元格不会删除已有值。
- 导入的学生、教师没有账户。通过 [账户邀请](14-merge-and-invitations.md#账户邀请) 发送注册邀请。

```csv
student_number,program,admission_date,year_level,status,family_name,given_name,name_ko,birth_date
202600001,B-CSE,2026-03-02,1,enrolled,Kim,Minsu,김민수,2007-05-01
```

课程版本的导入见[第 17 章](17-courses-and-curriculum.md)，选课限制的导入见[第 20 章](20-registration.md)。

## 选课限制

使用 **选课 > 选课限制** 列表上方的 **CSV 导入**（`设置和解除选课限制，批准规则例外` 权限）或 `uv run manage.py reference_import registration_holds`。用于导入旧系统（YUSTIC）的 `SRDENY` 数据或财务部门的欠费名单。

| 必填列 | 可选列 |
|---|---|
| `student_number`、`hold_type`（`unregistered`、`financial`、`academic`、`administrative`、`other`）、`reason` | `starts_at`（默认：导入时刻）、`ends_at`、`blocks_registration`（默认 1）、`blocks_grades`、`blocks_certificates` |

- 每行创建一条新限制（来源 `import`）。同一文件导入两次会生成两条限制，因此重新导入前请先确认列表。
- 时间写作 `2027-03-15` 或 `2027-03-15 09:00`（没有时区时按服务器时区 UTC）。`ends_at` 必须晚于 `starts_at`。
- 学号不存在的行会失败。解除在界面上连同原因一起办理（[第 20 章](20-registration.md)）。

```csv
student_number,hold_type,reason,ends_at
202312345,financial,2027-1 学费未缴,
202254321,academic,需要学业警告面谈,2027-03-15
```
