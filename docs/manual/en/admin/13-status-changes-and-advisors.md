# 13. Status changes and advisors

Menu: **Students and staff > Status changes**, **Status change types**, and the **Status changes** and **Advisors** tabs on a student record

## Student status

| Status | Meaning |
|---|---|
| Enrolled | Can register for courses |
| On leave | Record kept, cannot register |
| Withdrawn, Dismissed | Record ended. Readmission creates a new record |
| Graduated | Graduation date required. The account stays with alumni access |

Enrolled and on leave count as "current students" (student number sign-in, advisor assignment, etc.).

## Status change types

Each type defines the **New status**, the **Allowed from statuses** and whether **Students can request** it. Installation creates leave of absence, return, withdrawal, dismissal, readmission and graduation. Names can be changed, and changed names survive a reinstall.

## Student requests and approval

1. The student submits a request under **My records** in the portal with the type, effective date and reason. A record can have only one pending request at a time, and the student can cancel it before it is decided.
2. Staff **Approve** or **Reject** it in the **Status changes** list (default: pending). A rejection requires a note. Use the action menu of each row; a window asks for the note.
3. On approval, the record's status changes immediately and the change is added to the history.

- Requires the `Approve and record status changes` permission; only records within the permission scope (org unit, program) can be decided.
- You cannot approve a request you submitted yourself (separation of duties).
- If the record's status changed after the request was made (for example a leave already recorded another way), the request cannot be approved. Reject it and ask for a new request.

## Direct recording by staff

Dismissals, requests received on paper and similar cases are recorded directly with **Record status change** on the student record. A reason is required and the person recording it is stored as the approver. Requires the `Approve and record status changes` permission.

Every change is written to the activity log and the data changes ([chapter 4](04-audit.md)).

## Advisors

Under **Assign advisor** on the student record, choose the instructor, the role (Primary advisor, Co-advisor) and the start date (`Assign advisors` permission).

- There is one primary advisor. Assigning a new primary advisor ends the previous assignment the day before the start date, keeping the history.
- Only currently employed instructors can be chosen.
- Advisors see their current advisees under **Advisees** in the portal and can view those students' records.
