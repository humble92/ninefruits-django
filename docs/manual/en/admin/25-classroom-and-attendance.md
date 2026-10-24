# 25. Instructor Classroom and Attendance

Menu: instructors use the portal **My teaching > Roster and attendance** (`/portal/sections/{section ID}/attendance/`), students the portal **Attendance** (`/portal/attendance/`). Staff use the **Class meetings** tab of the **Curriculum and sections > Sections > Change** screen in the administration panel.

| Who | What they can do |
|---|---|
| Assigned instructors | Roster (with photos) and CSV, attendance sheet PDF, generating, adding and cancelling class meetings, entering attendance |
| Staff with `Plan sections` (within scope) | Same as instructors + class meetings in the administration panel |
| Staff with `View sections` (within scope) | Roster, attendance sheet, viewing attendance |
| Students | Their own attendance |

Classroom features such as announcements, assignments and materials are left to the LMS (porting plan section 12).

## Differences from the legacy system

- **The legacy system (YUSTIC) did not record attendance.** Its "attendance sheet" was a PDF that printed empty boxes (27 to 34 of them, varying by copy) next to the roster, with no dates and no totals. The new system creates **class meetings** from the meeting times, records present, late, absent or excused per meeting, and prints the records and totals on the attendance sheet PDF.
- **Roster.** The legacy instructor screen showed only student numbers and names (and exposed the resident registration number and address in a popup) and had no Excel download. The new system shows only student number, name, photo, program, year level and contact email, and downloads as CSV. Downloads are recorded in the audit log.
- **Instructors' access to their students.** A row level security policy (`student_records_instructor_select`, function `util.taught_student_record_ids()`) lets instructors see the student records and people of the students in their sections, and the application's visibility rules match it (before, the original showed only their advisees, which left names empty even on the grade entry screen).

## Class meetings

- **Generate**: one meeting per occurrence of the weekly meeting times (day, time, period). Instructors use the **Generate from meeting times** button; staff use the **Generate meetings** button above the **Class meetings** tab (with a confirmation page) or the command `uv run manage.py attendance_generate_sessions {term}` (whole term). Existing meetings and attendance are left alone, so it can be run again after the meeting times change. Cancelled sections are skipped.
- **Add a meeting**: a class outside the meeting times, such as a make-up class (date, start, end). Only dates within the session, and only one meeting per date and start time.
- **Cancel**: cancel the meeting with a reason. The meeting stays but is left out of the totals. **Restore** brings it back.
- There is no holiday calendar. Cancel the meetings on public holidays (once a term calendar is added, the generator can leave them out).

## Entering attendance

Under the meeting's **Attendance**, choose present, late, absent or excused for each student, add a note (200 characters) and **Save attendance**. The quickest way is **All present** (marks everyone present without saving) and then changing the exceptions.

- Attendance can be entered from the day of the meeting (not for future or cancelled meetings).
- Saving again records only the students who changed, and the audit event (`attendance.recorded`) keeps the old and new value per student.
- Clearing the status puts the student back to "not recorded".
- Only enrolled and completed students can be recorded (dropped and withdrawn students are not on the roster).

## Totals

| Item | Definition |
|---|---|
| Meetings held | Meetings that are not cancelled and lie on or before today |
| Attendance rate | (present + late + excused) ÷ meetings held × 100, one decimal (halves rounded up) |
| Not recorded | Meetings held without a record |

There is no rule converting a number of late marks into an absence or giving an F above one third of absences. It differs between universities, so instructors reflect attendance in the grade themselves. The counting rules live in one service (`AttendanceSummary`), so the roster, the attendance sheet and the student page show the same numbers.

## Attendance sheet PDF and roster CSV

Both downloads are recorded in the audit log (`attendance.sheet_exported`, `attendance.roster_exported`). CSV values starting with `=`, `+`, `-` or `@` (or a tab or line break) are exported with a leading single quote so they are not run as formulas.

- **Attendance sheet (PDF)** (`/sections/{section ID}/attendance-sheet`): landscape A4. Students down, meetings across (cancelled ones left out), O/△/X/E marks and totals per student. Meetings still to come are blank, so it also serves for recording by hand. When the PDF server (Gotenberg) does not answer, "The PDF could not be created" is shown.
- **Roster (CSV)** (`/sections/{section ID}/roster.csv`): student number, name, program, year level, contact email, registration status. UTF-8 with BOM, so it opens directly in Excel.

## Student portal

**Attendance**: per term (by default the latest term that has started) and course, the numbers present, late, absent and excused and the attendance rate; expanded, the record per meeting held (only what the instructor entered, otherwise "Not recorded").

## Operating procedure

1. Before the term starts, finalize the meeting times of the sections ([chapter 18](18-sections-and-timetables.md)).
2. Create the meetings with `uv run manage.py attendance_generate_sessions {term} --actor=...` (instructors can also create them on screen). One section only: `--section=CSE2010-01`; only the number of sections: `--dry-run` ([operations commands](../operations/commands.md)).
3. Run it again when meeting times change. Meetings of removed times are not deleted automatically; cancel them.

## Screens in this installation

The screens and features are those of the original (Filament, Livewire); some controls work slightly differently.

- **Class meetings** tab of the section change screen in the administration panel: date, time, room, status, records entered, reason. A row's **Cancel** opens a page for the reason, **Restore** a confirmation page. **Generate meetings** is an action button at the top of the screen. Staff with only `View sections` see the tab without the buttons.
- In the instructor portal, **Cancel** opens a reason field in the meeting row; enter the reason and press **Cancel** again (instead of the original's browser prompt).
- The **Attendance** entry page ends in `?meeting={meeting ID}`, so it can be bookmarked. **Back** returns to the roster and the meeting list.
- Under row level security the roster is filled only for people who can see the enrollments and student records. The default roles (Academic Affairs, Department Assistant) hold `View registrations and rosters` and `View student records` as well. A role given only `Plan sections` sees an empty roster and sheet (as in the original).

[Administrator manual contents](README.md)
