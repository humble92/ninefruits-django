# 20. Registration

Menu: **Registration > Registrations**, **Holds**, **Rule overrides**, **Registration rules**, **Credit limits**, **Registration attempts**, and the **Roster** and **Waitlist** tabs of the **Curriculum and sections > Sections** edit screen

| Permission | What it allows |
|---|---|
| `View registrations and rosters` | View registrations, rosters and registration attempts |
| `Register, drop and withdraw students for them (with a reason)` | Staff registration, dropping and withdrawing, removing from the waitlist and promoting immediately. Assigned with an org unit scope, only the sections offered by that unit |
| `Place and release holds, grant rule overrides` | Holds, rule overrides. Assigned with a scope, only the students in that scope |
| `Manage registration rule sets and credit limits` | Rule sets per term, credit limits |

Role defaults: Registrar has all four permissions, Academic Affairs has viewing plus rules and credit limits, Department Assistant has viewing and registration adjustments (assigned with the department's scope).

The lists show only students whose records you can see and registrations of sections in your scope. Row level security in the database applies the same scope.

## Differences from the legacy system

- Rules hard-coded on student number digits or department codes in the legacy system (YUSTIC), such as credit limits or excluding credit bank courses, became **per-term settings**. The legacy YUST rules are reproduced by the installation profile `yust-legacy` (below).
- When a request is refused, **every reason is shown at once** (legacy stopped at the first one). Every attempt and the result per rule is kept in the **Registration attempts**.
- The legacy credit limit bug for the nursing faculty with student numbers from 2014 on (18 credits applied where it should have been 21) is not reproduced. 21 credits apply.
- There is no textbook purchase entry during registration.

## Preparing a term

1. **Term windows** ([chapter 10](10-terms.md)): registration cart, registration (staggered opening per year level), add/drop, withdrawal. Add/drop and withdrawal windows are set per session.
2. **Registration rules > Prepare rules for a term**: choose the term and an earlier term to copy from. Leave it empty to start from the defaults. A term without a rule set uses the defaults.
3. **Credit limits**: limits per term type and group of students (below).
4. **Sections**: capacity, reserved seats (reserved seats and their opening time), **Waitlist size** ([chapter 18](18-sections-and-timetables.md)). A section must be **published** to take registrations.
5. **Holds**: enter the list of students with holds, e.g. unpaid tuition (CSV import possible, [chapter 9](09-csv-import.md)).
6. Check: `uv run manage.py registration_preflight 2027-SP` ([operations commands](../operations/commands.md)). It reports the windows, rule set, capacities and the number of students without a credit limit.

## Rules

All rules are checked in the order below. **Window, section open and seats** always apply and are not in the list.

| Rule | What it checks | Parameters |
|---|---|---|
| Registration period | A term window matching the student's target criteria must be open. Dropping needs the registration window or the add/drop window of the course's session; withdrawing needs the session's withdrawal window | None |
| Holds | Refused when a hold blocks registration | None |
| Student status | Only the chosen student statuses (default: enrolled) may register | Allowed statuses |
| Section eligibility | The section's eligibility and exclusion criteria | None |
| Same course twice | A course only once per term | None |
| Time conflict | Refused when the time overlaps with another registered section. First and second half of a term with non-overlapping dates do not conflict | Allowed overlap (minutes) |
| Credit limit | Total registered credits ≤ the applicable credit limit. Courses whose "Counts toward the credit limit" setting is off are not counted | None (set on the Credit limits screen) |
| Prerequisites | Prerequisites passed (equivalent courses count, minimum grade); corequisites may be registered in the same term | None (set on the course screen) |
| Retakes | Whether a passed course may be taken again | Retakes allowed, maximum attempts, only below a grade |

The rule set page lists its rules; **Edit** on a row opens the page of that rule. Each rule has its own settings.

- **On**: when off, the rule is not checked.
- **When not met**: Block or Warn only. With a warning the registration goes through and the student only sees a message.
- **Overrides allowed**: must be on for rule overrides and the "Waive rules" field of staff registration to take effect. It is off by default for holds and same course twice.
- Parameters appear only for their rule (student status: allowed statuses; time conflict: allowed overlap in minutes; retakes: retakes allowed, maximum attempts, below grade). An empty optional value means "no limit".

Retakes are detected automatically and the registration is marked **Retake**. How a retake counts in the GPA is described in [chapter 21](21-grades.md).

When a new release adds a rule to the catalog, installing it (`setup_install`) adds that rule with its defaults to the existing rule sets. Settings changed by administrators are kept.

## Credit limits

Set the term type (empty: every term type), the students (year level, admission year, program, org unit), the maximum credits and the priority. When several limits match a student, only **the one with the highest priority** applies. When none matches there is no limit (`registration_preflight` reports this).

Example: the legacy YUST rules (`yust-legacy` profile)

| Term type | Students | Maximum | Priority |
|---|---|---|---|
| Terms 1 and 2 | Admitted 2014 or later, nursing faculty (org unit code `NURS`) | 21 | 40 |
| Terms 1 and 2 | Admitted 2014 or later | 18 | 30 |
| Terms 1 and 2 | Admitted 2013 or earlier, nursing faculty | 20 | 20 |
| Terms 1 and 2 | Admitted 2013 or earlier | 17 | 10 |
| Summer and winter | Admitted 2014 or later, nursing faculty / others | 6 / 5 | 40 / 30 |
| Summer and winter | Admitted 2013 or earlier | 6 | 10 |

For credit bank courses whose codes start with `009` or `900`, turn off "Counts toward the credit limit" on the course. The profile is installed with `uv run manage.py setup_install --profile=yust-legacy` (it includes the Korean university profile). Running it again repairs the limits of the same names.

## Seats and waitlist

- A seat is secured at the moment of registration by locking the section row. Even when many students register at once the capacity is not exceeded.
- **Reserved seats** (e.g. 30 seats for majors) are used only by their students until the opening time. Reserved seats left over become open seats at the opening time. The portal shows them as "open, reserved, total".
- When the **Waitlist size** is greater than 0, students can **Join waitlist** of a full section. Joining the waitlist also requires passing every rule except seats.
- When a seat is freed by a drop, a withdrawal or the release of reserved seats, waiting students are **promoted automatically** in order (a background task; one promotion per section at a time). Every rule is checked again on promotion. A student who meanwhile registered for another course and now exceeds the credit limit or has a time conflict is removed from the waitlist with the reason recorded. The student receives an email. Anything missed is handled hourly by `waitlist_promote`.
- Once the registration and add/drop windows have all closed, the remaining waitlist entries expire.
- The capacity cannot be reduced below the number of students already registered.

There is no way to reorder the waitlist. To place a particular student first, use **Register a student** (raise the capacity if the section is full).

## The student's screen

In the portal under **Registration** (`/portal/registration/`) the student chooses the term, searches by course code or title and registers, adds to the cart or joins the waitlist. The screen shows the state of the registration period (open, cart only, opening time), registered credits against the credit limit and the timetable. On phones the timetable is a list per weekday.

- **Cart**: during the cart window students collect courses and, once registration opens, **Register all**. Adding to the cart runs the rules in advance and reports problems, but only the window, section open and same course twice checks prevent adding. The rules are checked again on registration.
- The drop and withdraw buttons change with the term windows. A withdrawn course stays in the history as **Withdrawn** (shown as W on the grades screen, [chapter 21](21-grades.md)).
- Register, join waitlist, add to cart and register all are limited to 30 requests per minute per person.

## Registrations and staff adjustments

**Registrations**: filter by term and status, search by student number or name. By default it shows the registered entries of the current (or next) term.

**Register a student** (at the top of Registrations, or the button at the top of the section page): enter the student number, the section (only when opened from Registrations: the published sections of the current term), the rules to waive, whether to add to the waitlist if full, and the reason.

- The same rules as for students are checked. **The registration period does not apply to staff registration.**
- "Waive rules" only works for rules with **Overrides allowed** on. Section open and seats cannot be chosen (raise the capacity instead).
- The result (registered, waitlisted, refused with reasons) is shown as a message at the top of the screen. It is recorded in the activity log with the reason.

**Drop and withdraw**: from the row menu in Registrations or **Drop** / **Withdraw** in the section's **Roster** tab, with a reason. Possible regardless of the term windows. When a seat is freed, waitlist promotion follows.

**Waitlist** tab (sections with a waitlist size or waitlist entries): in request order, with status and outcome note. **Remove** on a row takes a student off with a reason. After raising the capacity, **Promote now** at the top of the page promotes at once.

## Holds and rule overrides

**Holds** (legacy registration denial `SRDENY`): **Place a hold** with the student number, hold type (Not registered for the term, Financial, Academic, Administrative, Other), effect (blocks registration / grade viewing / certificates), start and end, reason. Grade viewing and certificate blocks are off by default. Besides unpaid tuition they serve administrative cases where grades must be withheld for a while, such as an investigation of academic misconduct. With a grade viewing block the student cannot see the portal grade screen or the grade report ([chapter 21](21-grades.md)). Staff screens and grade entry by instructors are not affected. With a certificate block, staff cannot issue certificates ([chapter 23](23-certificates.md)). Holds are not deleted; they are **released** with a reason from the row. The default list shows the holds in force. **Import CSV** above the list loads a list at once ([chapter 9](09-csv-import.md#registration-holds)).

**Rule overrides** (legacy registration allowance `SRALLOW`): **Grant an override** with the student number, term, rule, what it applies to (empty: the whole term, or a section as `COURSE-SECTION` or a course code), expiry, reason. With an override the registration goes through even when that rule fails (as long as the rule has Overrides allowed on). The registration period rule can be opened by an override too (e.g. a graduating student who missed the window). Section open and seats cannot be overridden. **Revoke** an override from its row once it is no longer needed.

## Registration attempts

Every registration, drop, withdrawal, waitlist, promotion and cart attempt is kept with its time, outcome, rules not met and messages, the staff member or student who did it, and the request ID. Filter by term, outcome and action, search by student number. For "why could I not register" questions, search by student number. What would happen if the student registered now can be previewed with `uv run manage.py registration_simulate {student number} {course code-section number}` (nothing is saved or logged).

[Administrator manual contents](README.md)
