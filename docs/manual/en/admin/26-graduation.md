# 26. Degree Audit and Graduation

Menu: **Graduation > Degree audits**, the **Degree audit** button on the student record view screen, **Settings > Graduation settings** (degree number pattern, minimum cumulative GPA; `Process graduations` permission). Students see their own progress in the portal under **Graduation requirements**.

| Permission | What it allows |
|---|---|
| `Run and view degree audits` | Run audits (single and bulk) and view stored audits |
| `Process graduations, grant requirement waivers` | Process graduations (bulk), requirement waivers |

Role defaults: Registrar has both, Academic Affairs has audits.

## Differences from the legacy system

- **Requirements are checked.** The legacy system (YUSTIC) graduation audit sheet only printed the credits and GPA per course category and did not compare them with anything (the audit result box was empty). The new system compares with the **graduation requirements** per catalog year ([chapter 17](17-courses-and-curriculum.md)) and reports whether each requirement is satisfied.
- **An audit is required before graduation.** In the legacy, entering status change code Z was all. The new system processes a graduation only when the latest stored audit is satisfied.
- **The system issues the degree number.** The legacy did not use the degree number field and wrote the diploma number by hand.
- Graduates are not moved to another table. Only the student status changes to `Graduated` and the account keeps alumni access ([chapter 13](13-status-changes-and-advisors.md)).

## Audit rules

The requirement set for the student's **primary program × catalog year** is found and every requirement is checked.

| Requirement kind | Check |
|---|---|
| Credits in a category | Sum of the credits of passed courses whose category is that category **or a category below it** ≥ minimum credits |
| Required courses | Every course in the list passed. **Equivalent courses** in effect at the time of registration count |
| Choice from courses | Credits or number of passed courses from the list (equivalents included) at or above the threshold |
| Passed examination | A passed result of that examination kind exists ([chapter 24](24-assessments.md)) |

- "Passed" means a registration whose finalized grade is passing (`is_passed`). Courses passed on the same person's other student records (before a readmission) count too.
- The requirement set's **total credits** and the **minimum cumulative GPA** of **Settings > Graduation settings** (default 2.0; empty: not applied) are checked as well.
- Second majors and minors are checked separately against their own requirement sets and shown together. The condition for graduation is that the primary program is satisfied.
- Without a requirement set matching the catalog year the audit is not satisfied (the set must be created).

## Audits

- **Audit now**: the **Degree audit** button on the student record view screen. It checks the current data at once and shows the passed and missing courses per requirement. **Save this audit** stores it.
- **Bulk audits**: **Degree audits > Run audits** (term, from year level) or the command `uv run manage.py degree_audit_run --term={term} --min-year-level=4 --actor=...` ([operations commands](../operations/commands.md)). An audit is stored for every enrolled student.
- A stored audit is a **snapshot**. Later grade changes do not alter it; auditing again adds a new snapshot. The list shows only the **latest** audit per student and program role, and graduation processing looks at the latest audit too.

## Waivers

A single requirement is waived for individual circumstances such as a change of major, transfer admission or an exchange. Two people are involved (decision of 2026-10-23).

1. **Request**: under **Waive a requirement** on the student record view screen, choose the requirement and give the reason (`Process graduations, grant requirement waivers` permission). Audit event `graduation.waiver_requested`.
2. **Approve or reject**: under **Graduation > Requirement waivers**, **another staff member** with the same permission approves (note optional) or rejects (note required). Nobody can decide their own request. Audit events `graduation.waiver_approved`/`waiver_rejected`.
3. Only approved waivers count as satisfied in the audit. One pending or approved waiver per requirement.
4. **Lift**: **Lift the waiver** on an approved waiver (reason required) stops it from applying and keeps the history (status `Lifted`, audit event `graduation.waiver_lifted`). The graduation of a student already processed is not undone.

Every step also appears in the data change record.

## Processing graduations

In the **Degree audits** list select the students and click **Graduate** (graduation date, reason). For each student:

1. Checks that the student is enrolled and the latest primary program audit is satisfied. Otherwise that student is skipped and the reason is reported.
2. Records the status change `Graduated` (status `Graduated`, graduation date). It appears in the status change history of [chapter 13](13-status-changes-and-advisors.md).
3. Issues the degree number. The pattern is `{PROGRAM}-{YYYY}-{SEQ:5}` of **Settings > Graduation settings** (default, e.g. `CS-2026-00001`; tokens `{PROGRAM}` program code, `{YYYY}`, `{YY}` graduation year, `{SEQ:n}` sequence per prefix). Concurrent processing never collides.
4. Audit event `graduation.processed` (student number, graduation date, degree number, the audit it was based on).

Graduates keep seeing their grades and certificates in the portal, and the certificate of graduation prints the graduation date and degree number ([chapter 23](23-certificates.md)). A wrong graduation is corrected with a status change (readmission and the like). There is no function to undo a graduation.

## Frequently asked questions

- **The audit says "no requirement set".** The program has no graduation requirement set covering the student's catalog year. Create one as in [chapter 17](17-courses-and-curriculum.md).
- **An equivalent course is not recognized.** The effective period of the equivalence must include the start date of the term in which the course was taken.
- **What happens when I change the degree number pattern?** It applies from the next issue on. When the prefix changes, the sequence starts again at 1.

## The screens of this installation

The screens and functions are those of the original (Filament, Livewire); some controls work slightly differently.

- **Graduation > Degree audits** list (`/admin/graduation/degreeaudit/`): the filters default to program role **Primary program** and student status **Enrolled**. **Open** on a row shows the stored audit; **Audit again** opens a confirmation page. **Run audits** is the action button above the list (term, from year level, default 4).
- To **Graduate**, tick the rows, choose **Graduate** in the action list and run it: a page asks for the graduation date and the reason. Students who could not be processed are listed with their student number and the reason as warnings (up to 10).
- **Degree audit** on the student record shows the audit evaluated now on its own page; **Save this audit** below stores it. **Waive a requirement** opens a page to choose the requirement and give the reason.
- **Graduation > Requirement waivers** (`/admin/graduation/degreerequirementwaiver/`): the status filter defaults to **Pending** and the menu shows the number pending. **Approve**, **Reject** and **Lift the waiver** on a row open a page for the note (reason). Opening them for your own request or for a waiver already decided returns 403.
- **Settings > Graduation settings** (`/admin/settings/graduation/`): the degree number pattern is saved only with exactly one `{SEQ:n}`. The minimum cumulative GPA is 0 to 5; empty means not applied.
- Portal **Graduation requirements** (`/portal/graduation/`): in the menu of students and alumni. With several student records (readmission) it uses the record chosen in the portal.
- Graduation writes the status change and the degree number in the system context after checking the permissions (graduation processing, the record's scope, the status change approval scope), so graduation staff do not also need `Manage student records`. The data change log still names the user who processed it.

[Administrator manual contents](README.md)
