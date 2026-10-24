# 9. CSV import

Use the **Import CSV** button at the top of the org unit, program, building, room and code list screens (`Import reference data from CSV` permission). Student record, instructor, course and registration hold imports are added the same way by their phases. Very large files can be imported the same way by the IT operator with the `reference_import` command.

## Common rules

- The first line holds the column names (tables below). Encoding is UTF-8; in Excel, save as "CSV UTF-8".
- A row whose code already exists **updates** that record. Importing the same file again does not create duplicates.
- Per-language columns use the form `column_language`: `name_en`, `name_ko`, `name_zh-hans`. New rows require the English name (`name_en`). Empty cells do not erase existing translations.
- Dates are written as `2026-03-01`; yes/no as `1`/`0` or `true`/`false`.
- The header is checked first (if a required column is missing, nothing is imported). Files of up to 500 rows are imported right away; larger files are processed in the background (Celery). The result appears on the import page under **Reference data > CSV imports** (rows imported, failed rows and their reasons). If rows failed, **Download failed rows** gives a CSV with the reason per row. Fix it and import just that file again.
- Column names must match the tables below; unknown columns are ignored. The original system's `name_zh_CN` column name is accepted as `name_zh-hans`.

## Column formats

| Kind | Required columns | Optional columns |
|---|---|---|
| Org units | `code`, `type` (org unit type code), `name_en`, `effective_start_date` | `parent` (parent code), `name_ko` etc., `short_name_*`, `effective_end_date`, `sort_order` |
| Programs | `code`, `org_unit` (org unit code), `degree_level`, `name_en`, `effective_start_date` | `degree_title_*`, `standard_duration_years`, `effective_end_date`, `allows_second_major`, `allows_minor` |
| Buildings | `code`, `name_en` | `name_*`, `address`, `is_active` |
| Rooms | `building` (building code), `code` (room number) | `name_*`, `room_type` (room type code), `org_unit`, `capacity`, `is_schedulable`, `is_active` |
| Code values | `type` (list code), `code`, `name_en` | `name_*`, `sort_order`, `is_active` |

`degree_level` values: `associate`, `bachelor`, `master`, `doctorate`, `certificate`, `non_degree`

For org units, parent units must come first (sort as university → college → department).

## Example: org units

```csv
code,type,parent,name_en,name_ko,effective_start_date
UNI,university,,Sample University,샘플대학교,1990-03-01
ENG,college,UNI,College of Engineering,공과대학,1990-03-01
CSE,department,ENG,Computer Science,컴퓨터공학과,1995-03-01
```

Imports for students and instructors (Phase 2) and courses (Phase 4) are added together with those features.
