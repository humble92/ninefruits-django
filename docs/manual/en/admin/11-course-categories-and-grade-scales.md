# 11. Course categories and grade scales

## Course categories

Menu: **Reference data > Course categories** (`Manage course categories` permission). Replaces `SFOBJDIST` of the legacy system (YUSTIC).

The classification of courses, such as general education required or major elective. Categories can be grouped by setting a **Parent** (for example General education → General education required, General education elective). Graduation requirements (Phases 4 and 11) refer to them, as in "30 credits of major required courses".

## Grade scales

Menu: **Reference data > Grade scales** (`Manage grade scales` permission). Replaces `SSCOREDEF` of the legacy system.

| Scale field | Description |
|---|---|
| Maximum grade points | For example 4.5 |
| Default | Only one scale can be the default. It can be turned on only while no scale is the default (see below) |

Open a scale and add grades under **Grades** below.

| Grade field | Description |
|---|---|
| Grade | For example `A+`, `P` |
| Grade points | Required for grades that count in the GPA |
| From/To (%) | Raw score conversion bands (optional), for example A+ 95–100 |
| Counts in GPA | Turn off for grades that are excluded from the GPA, such as P/NP |
| Passing | Turn off for grades that earn no credit, such as F or NP |
| For | Graded courses (letter grades), Pass/fail courses (P, NP) or Both (for example I, incomplete). The grade entry screen only shows the grades that match the course's grading basis |

**The default scale is fixed at installation and cannot be changed** (decision of 2026-10-23), because every grade and GPA is expressed in that scale. Set it with `setup_install --grade-scale=4.5|4.3`; without the option, the first profile's scale becomes the default. The default flag cannot be changed on screen and the default scale cannot be deleted. Score bands and grade points per grade are edited on this screen ([chapter 21](21-grades.md)).

Scales loaded by the profiles

- Korean university: 4.5 scale (`KR45`): A+ 4.5 (95–100), A0 4.0 (90–), B+ 3.5 (85–), B0 3.0 (80–), C+ 2.5 (75–), C0 2.0 (70–), D+ 1.5 (65–), D0 1.0 (60–), F 0, P, NP
- `--grade-scale=4.3` or the legacy YUST profile: 4.3 scale (`KR43` or `YUST43`): A+ 4.3 (97–100), A0 4.0 (93–), A- 3.7 (90–), B+ 3.3 (87–), B0 3.0 (83–), B- 2.7 (80–), C+ 2.3 (77–), C0 2.0 (73–), C- 1.7 (70–), D+ 1.3 (67–), D0 1.0 (63–), D- 0.7 (60–), F 0, P, NP (the legacy profile also includes N and I). The score bands start at 3-point intervals, so adjust them to the school's standard.

A scale that has already been used in grades cannot be deleted.
