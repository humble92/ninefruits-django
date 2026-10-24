# 7. Org units and programs

Menu: **Reference data > Org unit types**, **Org units**, **Programs**

## Org units

Universities, colleges, departments, majors and administrative offices are managed on one screen. They replace the colleges (`SFCOLLEGE`) and departments (`SFDEPARTMENT`) of the legacy system (YUSTIC).

| Field | Description |
|---|---|
| Code | A permanent identifying code, for example `CSE` |
| Type | University, college, department, etc. (more can be added on the Org unit types screen) |
| Name, Short name | Per language |
| Parent | The unit this one belongs to. A unit cannot be moved under itself or under one of its own descendants |
| Valid from, Valid until | The period the unit existed. An empty end date means it is currently operating |

- The list shows **Currently valid only** by default. Turn off the filter to see past units as well.
- When an org unit is chosen as the scope of a role assignment, every unit below it is included. Example: College of Engineering scope = every department in the College of Engineering.

## Reorganizations

Past student records and grades must point at the unit as it was at the time, so a unit is not edited in place; the change is recorded as a **reorganization** instead.

1. Open the **Edit** page of the unit that disappears (or changes).
2. Press **Reorganize**.
3. Choose the change type.
   - **Renamed**: create the unit with the new name first and designate it as the successor
   - **Merged**: when several units merge into one, designate the same successor from each unit
   - **Split**: when one unit is divided into several, designate several successors
   - **Moved**: when the unit moves under a different parent as a new unit
4. Enter the **Effective date** and a reason. The unit ends the day before the effective date, and the record appears in the **Successors** list below.

A simple typo is fixed by **editing** the name, not by a reorganization (the data change is recorded).

## Programs

Degree programs or major programs. Student records belong to a program (Phase 2).

| Field | Description |
|---|---|
| Code, Name, Degree title | Degree title example: Bachelor of Engineering |
| Degree level | Associate, Bachelor, Master, Doctorate, Certificate, Non-degree |
| Org unit | The department that runs the program |
| Standard duration | Standard time to completion (years) |
| Valid from, Valid until | The period the program exists, not the period it admits new students |
| Accepts second majors, Accepts minors | Whether students of other programs can apply for this program as a second major or minor ([chapter 19](19-second-majors-and-minors.md)) |
