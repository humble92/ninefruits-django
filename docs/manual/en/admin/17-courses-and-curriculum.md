# 17. Courses and Graduation Requirements

Menu: **Curriculum and sections > Courses**, **Graduation requirements** (permissions `Manage courses, versions and requisites`, `Manage graduation requirements`)

## Courses and versions

A course consists of an unchanging **code** and **versions** with effective periods. The title, credits, hours, course category, grading basis and requisites belong to the version. The legacy system (YUSTIC) distinguished courses by course code and start date, but grades pointed only at the course code, so it was ambiguous which version a student had taken. In the new system, sections and grades point at a version.

- The periods of versions of the same course cannot overlap (database constraint). On any given date exactly one version is in effect.
- A section is offered with the version in effect on the session's start date.

| Field | Description |
|---|---|
| Course code | e.g. `CSE2010`. The code carries no business meaning (rules such as the legacy `009*` credit bank check are replaced by the fields below) |
| Managing unit | The org unit that manages the course. The default offering unit of its sections |
| Title, Description | Per language |
| Credits, lecture and lab hours | In steps of 0.5 |
| Course category | Reference data > Course categories |
| Grading | Letter grade or Pass/fail |
| Counts toward the credit limit | When off, the course is left out of the registration credit limit (credit bank courses and the like) |
| Course evaluation | When off, the course is not evaluated (practicums, internships and the like; [chapter 22](22-course-evaluation.md)) |
| May be taken again for credit | Taking it again earns credits again instead of being a retake (seminars with changing topics and the like) |

## Revising a course

When the credits or the title change, do not edit the version; **revise** it instead. On the course **Edit** screen, in the **Versions** tab, click **Revise from a date** on the current version and enter the new version's start date, the changed values and the reason.

- The current version ends the day before the start date; the new version starts with a copy of the current version and its requisites.
- Sections already offered and past grades keep pointing at the earlier version.
- Edit a version directly only for corrections that do not change its meaning, such as typos (they appear in the data change record).

## Prerequisites and corequisites

Open a version from the **Versions** tab (the row's link); they are entered under **Requisites** at the bottom of the version screen. A new version is added with **Add course version** on the course screen.

| Field | Description |
|---|---|
| Kind | Prerequisite (must be completed first) or Corequisite (taken together in the same term; satisfied if already completed) |
| Group | Only one course in the same group needs to be completed (or). Every group must be met (and) |
| Minimum grade | A grade code of the default grade scale (e.g. `C0`). Empty: a passing grade |
| May be taken in the same term | When the prerequisite may be taken in the same term |

Example: group 1 contains `CSE1001`, group 2 contains `MAT1001` and `MAT1002` → `CSE1001` and (`MAT1001` or `MAT1002`). The prerequisite rule checks this during registration ([chapter 20](20-registration.md)).

## Equivalent courses

When a curriculum reform replaces a course, enter the replacement with its period in the **Equivalent courses** tab of the course **Edit** screen. With **Mutual** on, each course counts for the other; with it off, only the equivalent course counts for this one. Used by the retake check ([chapter 20](20-registration.md)) and the degree audit ([chapter 26](26-graduation.md)).

## Graduation requirements

One requirement set is created per program, **Program role** (primary program, second major, minor) and range of **catalog years**. A student is subject to the set matching the catalog year of their student record.

- Catalog years of the same program and program role cannot overlap. Leave the end year empty to keep the set in effect until the next set starts.
- Requirement kinds

| Kind | Input | Example |
|---|---|---|
| Credits in a category | Course category, minimum credits | 9 credits of general education (required) |
| Required courses | List of courses | All 4 required major courses |
| Choice from courses | List of courses, minimum credits or minimum number of courses | 12 credits from the major electives |
| Passed examination | Examination kind | Passed the English comprehensive examination ([chapter 24](24-assessments.md)) |

Second majors and minors get their own, smaller sets than the primary program (e.g. 36 credits for a second major, 21 for a minor). The requirements are checked by the degree audit ([chapter 26](26-graduation.md)).

## CSV import

**Import CSV** on the course list (permission `Manage courses, versions and requisites`) loads course versions in bulk. One row is one version. Courses are found by code (and created when missing); versions by code and start date, so importing the same file again updates, and a row with another start date becomes a revision. A row whose period overlaps fails on its own.

| Column | Description |
|---|---|
| `code` | Course code (required) |
| `org_unit` | Managing unit code. Required for new courses |
| `effective_start_date`, `effective_end_date` | Version period (`YYYY-MM-DD`) |
| `title_en`, `title_ko`, `title_zh-hans`, `title_lo` | Title per language. English is required for new courses |
| `credits`, `lecture_hours`, `lab_hours` | Credits (required for new versions, 0–30), hours (0–40) |
| `category` | Course category code |
| `grading_basis` | `graded` or `pass_fail` |
| `counts_toward_credit_limit` | `1`/`0` |

The same is available as `uv run manage.py reference_import courses <file> --actor=<email>` ([chapter 9](09-csv-import.md)).

[Administrator manual contents](README.md)
