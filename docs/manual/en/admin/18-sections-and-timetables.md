# 18. Sections and Timetables

Menu: **Curriculum and sections > Sections**, **Timetables** (permissions `View sections`, `Plan sections (instructors, times, rooms)`. Assigned with an org unit scope, they cover only the sections offered by that unit)

## Creating a section

1. Under **Sections > Create** enter the term's session, the course, the section number (e.g. `01`), the capacity and the offering unit. The title and credits come from the course version in effect on the session's start date.
2. In the tabs of the edit screen enter the **Meeting times**, **Instructors** and **Reserved seats**.
3. When everything is ready, **Publish** it. Only published sections appear in the portal **Course catalog** and can be registered for ([chapter 20](20-registration.md)).

| Status | Meaning |
|---|---|
| Draft | Being planned. Only staff and the assigned instructors see it |
| Published | Visible to students. Can be sent **Back to draft** |
| Cancelled | A reason is required. The room and instructor times are freed. **Reopen** turns it back into a draft; if another section has taken the time in the meantime it cannot be reopened |

Only draft sections can be deleted. A section that has been published is cancelled instead.

| Field | Description |
|---|---|
| Session | A session of the term ([chapter 10](10-terms.md)). Moving to another session changes the meeting dates and the course version to match that session |
| Who may register, Who may not register | Year level, admission year, program, org unit. Example: excluding the course's own majors from a general education course. Second major and minor students also count as students of that program |
| Language of instruction | e.g. `ko`, `en` |
| Waitlist size | Number of waitlist entries accepted once the section is full. 0: no waitlist ([chapter 20](20-registration.md)) |
| Evaluation (evaluation method) | Absolute evaluation (default; the instructor enters scores and grades are computed from them) or relative evaluation (grades only are entered, grade caps apply). The instructor requests a change from the grade entry screen and the section's staff approve it. It cannot be changed once grades have been entered ([chapter 21](21-grades.md)). Copied along when copying a term |

## Meeting times and rooms

In the **Meeting times** tab enter the day, start and end time and the room. Choosing a **Period** fills in the times. Leave the meeting dates empty to use the session's dates.

- Two sections cannot use the same room at the same time, and one instructor cannot teach two sections at the same time. The database enforces this; the screen shows the conflicting section, e.g. "The room is already booked at this time by OOO".
- When the dates do not overlap, as with the first and second half of a term, the same time and room can be used.
- Cancelled sections do not occupy any time.

## Instructors

In the **Instructors** tab assign instructors with a role (Instructor, Co-instructor, Teaching assistant). A section can have several. An instructor who already teaches another section at the same time cannot be assigned. Instructors manage the timetable and syllabus in the portal under **My teaching**.

## Reserved seats

In the **Reserved seats** tab set aside seats for groups of students (e.g. 30 seats for the program's majors). After the **Opens to everyone at** time, unused seats can be taken by anyone. The reserved seats together cannot exceed the capacity. They are applied during registration ([chapter 20](20-registration.md)).

## Syllabus

The instructor writes it in the portal under **My teaching** (it also opens from the **Syllabus** button on the section screen). They enter the overview, learning objectives, textbooks and materials, course policies, assessment (items and weights) and the weekly plan; once **Published** it is visible to students.

## Copying from another term

**Copy from another term** in the section list starts from the plan of an earlier term (usually the same term of last year). Check the result with **Preview only** first.

- Sections that were not cancelled and are within your scope are copied as drafts.
- Copied along: instructors still employed, meeting times and rooms, reserved seats (the opening time is shifted by the difference between the terms' start dates), the syllabus (as an unpublished draft).
- Sessions are matched by code (whole term if there is none). The course version is taken as of the new session's start date.
- Sections whose section number already exists in the target term are skipped; when a room is already taken, the section is copied without the room. The result notification lists the skipped sections and those that need a check.

IT operators can do the same with `uv run manage.py section_copy`.

## Timetables and checks

- **Timetables**: choose a term and a room or instructor to see the weekly timetable.
- Check before publishing: an IT operator runs `uv run manage.py schedule_check_conflicts <term code>` to find rooms smaller than the capacity, retired instructors, course version mismatches and reserved seats exceeding the capacity ([command reference](../operations/commands.md#schedule_check_conflicts)).

## Scope

The list and the screens show only sections of offering units within the `View sections` and `Plan sections` scopes. The meeting times, instructors and reserved seats tabs and the status buttons (Publish, Back to draft, Cancel section, Reopen) need `Plan sections` in a scope covering the section's offering unit. The timetable page starts with the term in session (else the next one). On phones it shows a list per weekday.

[Administrator manual contents](README.md)
