# 21. Grades

Menu: **Grades > Grade progress**, **Evaluation method requests**, **Grade changes**, **Term records**, **Settings > Grading policy**. Instructors use the portal **My teaching > Enter grades**.

| Permission | What it allows |
|---|---|
| `View grades, grade progress and term records` | View grade progress, term records and student grade reports |
| `Finalize and return grades, enter grades for instructors, close terms` | Finalize or return a section's grades, enter grades for instructors (regardless of the window), submit grades outside the grade caps as an exception, close terms, recalculate. Assigned with an org unit scope, only the sections offered by that unit |
| `Be told when staff submit grades outside the grade caps` | Receive exception submission notifications. Assigned with an org unit scope to department heads and the head of the academic office |
| `Request a change to a finalized grade` | Request changes for sections one does not teach (e.g. cancelling a grade for academic misconduct) |
| `Approve or reject grade changes (not your own requests)` | Decide grade change requests |
| `Manage GPA, retake, academic standing and honors policy` | Grading policy settings |

Instructors enter grades and request changes for their own sections without any permission. Role defaults: Registrar has viewing, finalizing, approving and exception review; Academic Affairs has viewing, change requests and policy; Certificate Officer and Department Assistant have viewing. Evaluation method requests are decided with the `Plan sections` permission.

## Differences from the legacy system

- In the legacy system (YUSTIC), a grade saved by the instructor was immediately final, and the academic office edited it directly on the screen. There was no reason and no approval step, and edits by some accounts did not even appear in the backup records. The new system has the stages **enter → submit → finalize**, and a finalized grade changes only when **someone else approves a change request**. Both the application and the database (triggers) enforce this.
- In the legacy system an instructor could save grades for sections they did not teach by manipulating the request. The new system checks the assigned instructors and the permission scope on the server and in the database.
- GPA, academic warnings and honors are not computed on the fly on every screen; they are stored as **term records**. At term close they become the official record of that term.
- A retake removes the earlier grade from the cumulative GPA only **after the new grade is finalized** (the legacy removed it at registration and did not undo it when the section was cancelled).
- The legacy only disabled the grades menu; the grades were visible through the address. The new system enforces grade viewing blocks on the server.

## Order of a term

1. **Term windows** ([chapter 10](10-terms.md)): a **Grade entry** window per session. Instructors enter and submit only during this window.
2. Instructors enter and submit grades. `uv run manage.py grades_remind_missing {term}` sends reminder emails to instructors who have not submitted.
3. On **Grade progress** finalize each section or return it to the instructor.
4. When every section is finalized, **Term records > Close term**. Term records, academic standing and honors are determined and the term moves to **Grades closed**.
5. Grades changed after that go through **Grade changes**.

## Grade scale and evaluation method

**The grade scale is fixed at installation and cannot be changed** (decision of 2026-10-23), because every grade and GPA is on that scale. Set it with `uv run manage.py setup_install --grade-scale=4.5|4.3`; otherwise the first profile's scale is used (Korean university 4.5, legacy YUST 4.3). The **default** mark under Reference data > Grade scales cannot be moved and the default scale cannot be deleted. The **score bands** (lower and upper %) and grade points of each grade are edited on that screen ([chapter 11](11-course-categories-and-grade-scales.md)).

Every section has an **evaluation method**. The default is **Absolute evaluation**.

| Evaluation method | Instructor enters | Stored | Submission condition |
|---|---|---|---|
| Absolute evaluation (default) | A **score (0–100)** per student. The grade follows from the score band and cannot be chosen (only grades without a score, e.g. I, are chosen directly) | Score (original), grade, grade points | A grade for every student |
| Relative evaluation | A **grade** per student. No scores are entered (refused if entered) | Grade, grade points | A grade for every student + **grade caps** respected |
| Pass/fail course | P/NP regardless of the evaluation method | Grade | A grade for every student |

- An instructor who wants relative evaluation clicks **Request Relative evaluation** (with a reason) on the grade entry screen. A holder of the `Plan sections` permission for the offering unit (department assistant, academic affairs) approves or rejects it (note required) under **Grades > Evaluation method requests**, and the instructor is told by email. On approval, draft grades entered under the old method are cleared. Once grades have been **submitted**, neither a request nor a change is possible. Staff can also change the method on the section screen, but only until grades are entered.
- Highest grade for a retake: under absolute evaluation, a score that would give a higher grade than the cap is **lowered to the cap grade** (the score stays). Under relative evaluation a grade above the cap cannot be chosen.

## Grade caps (relative evaluation)

**Settings > Grading policy > Relative evaluation**: cap per grade group (default A group 30%, B group 40%), tolerance above the cap (default 1 percentage point), minimum number of graded students for the check (default 10).

- Grade groups are by letter: A+, A0 and A- form the A group; B+, B0 and B- the B group. Groups without a cap (C, D, F) are unlimited.
- The denominator is the number of students in the section with a grade that counts toward the GPA. Withdrawn students and P/NP/I are left out.
- Sections below the minimum number of students are not checked (30% A out of 7 students cannot be met).
- Instructors see the current distribution against the caps with **Check grade caps** on the grade entry screen, and **cannot submit** above the caps.
- Staff with the grade management permission can submit above the caps, but as an **exception submission**: a reason is mandatory, the distribution and reason are recorded in the activity log, the holders of the `Be told when staff submit grades outside the grade caps` permission (department heads, head of the academic office, assigned with an org unit scope) get an email, and the section is marked **Submitted as an exception**. **Grade progress** can be filtered to exception submissions only.

## Grade entry (instructors)

In the portal under **My teaching** open the section's **Enter grades**. The top of the screen shows the section's evaluation method, entry instructions and the evaluation method request.

- Absolute evaluation: the grade appears as soon as the score is entered.
- Relative evaluation: only the grade is chosen. There is no score column. Check the caps with **Check grade caps** and submit.
- The list of grades follows the course's grading basis. Graded courses show letter grades, pass/fail courses show P/NP ([chapter 11](11-course-categories-and-grade-scales.md)).
- **Save draft** is possible at any time. Students do not see draft grades.
- **Submit grades** requires a grade for every student. After submission the instructor can no longer change them. For a wrong grade, ask the academic office to return the grades before finalization, or request a change after it.
- Withdrawn students show as W and get no grade.

## Finalizing and returning (academic office)

**Grade progress**: the sections of a term with the numbers not submitted, submitted and final. The **Ready to finalize** filter shows only sections where every student's grade has been submitted.

- **Finalize**: finalizes the submitted grades. The registrations become **Completed** and students see their grades. The students' term records are recalculated. Several sections can be chosen and finalized with **Finalize selected**. Sections with a student not yet submitted are skipped.
- **Return to instructor**: cancels the submission with a reason. The grades go back to draft and the instructor gets an email.
- **Grades**: opens the grade entry screen. The academic office can enter or change grades before finalization regardless of the window. When staff change a grade the instructor has **submitted**, the old and new values are recorded in the audit event `grades.submitted_changed`.

## Grade changes

The only way to change a finalized grade.

1. Request: the instructor clicks **Request change** for the student on the grade entry screen (with a reason; the new score under absolute evaluation, the new grade under relative evaluation). The retake cap also applies to changes. For sections they do not teach, staff with the `Request a change to a finalized grade` permission request it on the same screen. Only one open request per grade.
2. Decision: under **Grades > Grade changes** (default: the pending list; the menu shows the pending count) click **Approve** or **Reject** (note required). The requester cannot decide their own request (also enforced by a database constraint).
3. On approval the grade (score and grade under absolute evaluation) changes immediately, and the student's term record and the cumulative GPA of later terms are recalculated. Academic standing and honors keep the values determined at term close.

The requester can **Cancel request** while it is pending. Every request and decision is recorded in the activity log with its reason.

## GPA calculation

| Item | Rule |
|---|---|
| Attempted credits | Every finalized course (including F, P, NP, I) |
| Earned credits | Passing grades (excluding F, NP, I) |
| GPA credits | Grades included in the GPA. F counts with 0 points; P/NP/I are excluded |
| GPA | Sum (grade points × credits) ÷ GPA credits. A term with only pass/fail courses has no GPA |
| Decimals | Decimals and rounding (round half up, cut off) from the policy. Integer arithmetic, so there is no error at boundaries (e.g. 3.4375 → 3.438) |
| Term GPA | Every grade of that term (an earlier grade replaced by a retake still counts in its own term's GPA) |
| Cumulative GPA | A retaken course counts only once, by policy: **Latest attempt** (default; the latest even when it is worse) or **Best attempt**. The replaced grade is also left out of the cumulative credits and is shown on the grades screen as "replaced by a retake in the cumulative GPA" |

The retake relation is set at registration ([chapter 20](20-registration.md)): taking the same course or an equivalent course again links it to the earlier registration.

## Academic standing and honors (term close)

| Policy | Default | Legacy YUST profile |
|---|---|---|
| Warning threshold | Term GPA below 1.75 | Below 1.3 |
| Judge only regular terms | Yes | Yes |
| Warnings for dismissal review | 0 (off) | 4 |
| Count only consecutive warnings | No (total count) | No |
| Honors minimum GPA, minimum GPA credits | 4.0, 15 credits | 0, 0 (the legacy simply took the top N) |
| No honors with a failed course | Yes | No |
| GPA decimals | 2, round half up | 3, round half up |
| Grade scale (fixed at installation) | 4.5 (KR45) | 4.3 (YUST43) |
| Grade caps (relative evaluation) | A 30%, B 40%, tolerance 1 percentage point, checked from 10 students | Same |

- **Academic warning**: term GPA **below** the threshold. A term with only pass/fail courses gives no warning.
- **Dismissal review**: flagged when the number of warnings reaches the threshold. The dismissal itself is a status change ([chapter 13](13-status-changes-and-advisors.md)).
- When only regular terms are judged, summer and winter terms have no academic standing and do not break a run of consecutive warnings.
- **Honors**: students meeting the criteria are ranked per program by term GPA (ties share a rank; the next rank is skipped).
- The **Academic standing** of the student record changes to the latest result. The "academic standing" criterion of term windows and section eligibility uses this value.

On the **Term records** screen, filter by term, academic standing, honors and program to see the list of students on academic warning and the honors list (the legacy warning and honors reports). Run **Close term** first with **Preview only** (the default) to see the sections that are not final, then turn it off and run it again. **Recalculate** applies a changed policy to the records of past terms (reason required).

## Student screen and grade report

When a staff member opens a student's grade report it is recorded in the audit event `transcript.viewed` (with the student number).

- Portal **Grades**: finalized grades per term (withdrawals as W), term GPA and earned credits, cumulative GPA, academic standing, honors. Alumni can see it too. Grades that are not final are not shown.
- **Print**, **PDF**: an unofficial grade report for checking. The PDF is made by Gotenberg. The official transcript is issued as a certificate ([chapter 23](23-certificates.md)). Staff open a student's grade report with **Grade report** on the student record screen or in Term records (`View grades` permission).
- A student with **Blocks grade viewing** on in a **hold** cannot see the grades screen or the grade report ([chapter 20](20-registration.md)).
- During the course evaluation window, a student who has not finished the term's course evaluation has that term's grades hidden (a setting, [chapter 22](22-course-evaluation.md)).

## Grading policy

**Settings > Grading policy** (`Manage GPA, retake, academic standing and honors policy` permission). Changes the items of the table above. A changed policy applies from the next calculation on. To apply it to the records of past terms, **Recalculate**. Academic standing and honors are determined at term close, so they are not applied again to a closed term.

## Screens in this installation

The screens and functions are those of the original (Filament, Livewire); how they are operated differs slightly.

- Row menu of **Grade progress**: **Grades** (the portal grade entry screen), **Finalize** (a confirmation screen), **Return to instructor** (a reason screen). To finalize several sections, select them in the list and choose **Finalize selected** in the action list. Filters: term (default: the term in session, **All** for every term), offering unit, submitted as an exception, ready to finalize.
- **Approve** and **Reject** in the row menu of **Grade changes** and **Evaluation method requests** open a screen for the note. The default list shows pending requests, and the menu shows how many are pending.
- **Close term** above the **Term records** list: term, **Preview only** (on by default), reason. The preview shows in messages whether the term can close and the sections that are not final (up to 30). A started close runs as queued tasks (Celery) of 100 students each; a close in progress shows its progress above the term records list. When it finishes, the term moves to **Grades closed** and the staff member who started it gets an email. If a task fails, the close does not finish and the term stays as it is; fix the cause and close again (it gives the same result). From the command line: `uv run manage.py term_close {term} --dry-run`, `uv run manage.py term_close {term} --reason=...` ([commands](../operations/commands.md)).
- In **Grading policy**, write the grade caps as letters and percentages separated by commas, e.g. `A=30, B=40`. Empty means no cap.
- Portal grade entry: under absolute evaluation the grade appears next to the score shortly after it is typed. **Save draft**, **Check grade caps** and **Submit grades** are at the bottom of the screen; when saving fails (e.g. a score out of range) the entered values are shown again with the error. **Request change** on a student's row opens the request fields below the table.
- Staff grade report address: `/student-records/{student record id}/transcript/` (the **Grade report** button on the student record screen, **Grade report** on a term record row). Add `?format=pdf` for a PDF.
- Loading scores from the LMS is added to the grade entry screen in Phase 12. The grades of a term whose course evaluation is open and unfinished are hidden with a notice and a link to **Course evaluation** ([chapter 22](22-course-evaluation.md)).

[Administrator manual contents](README.md)
