# 10. Academic years, terms, term windows

Menu: **Reference data > Academic years**, **Term types**, **Terms**, **Class periods** (`Manage academic years, terms, term types and time slots` permission; term windows need `Manage term windows`)

## Differences from the legacy system

The legacy system (YUSTIC) decided the "current term" with a single term status flag (`AFS_CHECK`), which made it hard to process last term's grades and next term's registration at the same time. The new system has no "current term" setting. Instead, each task looks at the open **term windows** to decide which term applies. Grade entry for the previous term, classes in the current term and registration for the next term do not block each other.

## Academic years and terms

1. **Academic years**: code (for example `2026`), name, start/end dates. Academic years cannot overlap.
2. **Term types**: first term, second term, summer/winter intensive sessions, etc. The **Regular term** flag is used later by rules such as credit limits.
3. **Terms**: academic year, term type, code (for example `2026-FA`, for display only), name, class start/end dates. Terms of the same type cannot have overlapping class periods.

## Term status

| Status | Meaning | Term windows |
|---|---|---|
| Planned | In preparation. Not visible to students | Do not open |
| Published | In operation | Open |
| Grades closed | After grades are finalized | Open (grade appeals, etc.) |
| Archived | Finished | Do not open |

The status changes only through **Change status** on the term's **Edit** page. The order is Planned → Published → Grades closed → Archived; Published and Grades closed can be moved back one step. Changes are recorded with a reason.

## Sessions

A session is a period within a term in which classes run. Manage them on the **Sessions** tab of the term's **Edit** page.

- Creating a term creates the **Full term** session (code `FULL`) automatically; it follows the term dates when they change.
- Add sessions when some courses run for only part of the term, such as first-half and second-half 8-week courses or a 3-week intensive course. Example: `A` first half 9/1–10/25, `B` second half 10/26–12/20, `I` intensive 11/1–11/21.
- Sessions must lie within the term. If you shorten the term, fix the sessions that would fall outside first.
- Every section belongs to one session ([chapter 18](18-sections-and-timetables.md)). A university that does not use sessions needs only the full term session.

## Term windows

Add them under **Term windows** at the bottom of the term's **Edit** page.

| Field | Description |
|---|---|
| Window | Registration cart, Registration, Add/drop, Withdrawal, Grade entry, Grade appeal, Course evaluation, Graduation application, Second major and minor applications |
| Session | Only for course-bound windows (add/drop, withdrawal, grade entry, grade appeal, course evaluation). Default is the full term session |
| Opens, Closes | Times in the institution's time zone. The window closes at the closing time |
| Eligibility | Empty means everyone. Combine year levels, an admission year range, programs and org units (including descendants). A student must satisfy every condition |

There are two kinds of window.

| Kind | Windows | Reference |
|---|---|---|
| Course-bound windows | Add/drop, Withdrawal, Grade entry, Grade appeal, Course evaluation | The session the course belongs to. A second-half course follows the add/drop, withdrawal and grading windows of the second-half session |
| Student/term windows | Registration cart, Registration, Graduation application, Second major and minor applications | The whole term. No session |

**Creating windows per session**: on the Sessions tab, press **Copy windows** on a session to copy the course windows of another session (usually the full term) moved to this session's dates. Early windows (add/drop, withdrawal) keep their distance from the session start; late windows (grade entry, course evaluation) keep their distance from the session end. Check and adjust them after copying.

**Staggered opening example**: create three registration windows.

| Window | Opens | Eligibility |
|---|---|---|
| Registration | 10 February 10:00 | Year level 4 |
| Registration | 11 February 10:00 | Year level 3 |
| Registration | 12 February 10:00 | Year levels 1, 2 |

Each student's year level and admission year come from the student record data ([chapter 12](12-people-and-student-records.md)).

## Class periods

The unit of class time. Set the code (for example `1`), name (Period 1), start/end times and days. When entering a section meeting, choosing a class period fills in the start and end times. The Korean university profile loads ten 50-minute periods from 09:00 (Monday to Friday).

Class period times are "wall-clock" times independent of the time zone; they are stored exactly as entered.

Term window opening and closing times are entered and shown in the institution's time zone in the administration panel and stored in UTC.
