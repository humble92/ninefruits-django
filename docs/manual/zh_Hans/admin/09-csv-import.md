# 9. CSV 导入

使用组织单位、专业项目、楼宇、教室、代码数据列表界面上方的 **导入 CSV** 按钮（`通过 CSV 导入基础数据` 权限）。学籍、教师、课程、选课限制的导入将在相应的 Phase 中以同样方式添加。特别大的文件可由 IT 运维人员用 `reference_import` 命令以同样方式导入。

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

学生、教师（Phase 2）和课程（Phase 4）的导入随相应功能一起添加。
