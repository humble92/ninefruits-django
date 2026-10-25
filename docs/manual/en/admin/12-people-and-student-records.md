# 12. People and student records

Menu: **Students and staff > People**, **Student records**, **Instructors**

## How people and student records relate

| Concept | Description |
|---|---|
| Person | One human being. Name, birth date, contact details, identity numbers, photo, guardians. Whether student or instructor, one human being is one person |
| Student record | One admission. Student number, program, admission date, year level, status. A student who graduates and is readmitted gets a **new student record (new student number)** on the same person |
| Instructor | The person's instructor details (employee number, org unit, employment type, academic title). One per person |
| Account | The sign-in account. Linked 1:1 with a person. A person with several student records still has one account |

Students and graduates choose a student record in the portal (when there are several, a record selector appears at the top).

## People

- A person has both a **Romanized name** (legal name as in the passport: family name, given name) and a **Name in other languages** (for example Korean `김민수`). Screens show the name in the current language when there is one, otherwise the romanized name. Search finds both.
- National ID numbers and passport numbers are stored encrypted and shown masked. The full value is shown once on a separate page after pressing **Show national ID number** (or **Show passport number**) at the top of the person page and entering a reason (`Reveal national ID and passport numbers` permission). The value is not stored anywhere (no message or log), and the reveal is written to the security log with the reason. Searching by number finds exact matches only.
- Photos are uploaded on the person's edit page. A photo can only be downloaded after a permission check (there is no public address).
- Guardians are managed on the **Guardians** tab of the person's detail page. Students can also edit their guardians and contact details (email, phone, address, postal code) under **My details** in the portal. They cannot change their name, birth date or identity numbers.
- **Change history** at the bottom of the person page lists the latest 50 data changes of the person and their guardians (time, table, changed columns, user). With `View audit records` you can open each change (values before and after). The student record page shows the history of the record, its status changes, advisors and second majors and minors the same way.

| Permission | What it allows |
|---|---|
| `View all people` | View every person |
| `Create and edit people` | Create and edit people |
| `Reveal national ID and passport numbers` | See full national ID and passport numbers |
| `Merge duplicate people`, `Invite people to create an account` | [Chapter 14](14-merge-and-invitations.md) |

Staff without the `View all people` permission can still see the people and instructors behind the student records they are allowed to see.

## Registering a student

1. Press **Add student record** at the top of the **Student records** list (the page is titled **Register student**).
2. Choose an **Existing person** (readmission, an instructor entering graduate school, etc.) or enter a **New person**. Before creating a new person, search to check whether the same person already exists.
3. Enter the program, admission date, year level and admission type. The managing org unit is taken from the program.
4. Leave the student number empty to generate it with the student number pattern under **Settings > Student records**. The default pattern `{YYYY}{SEQ:5}` is the admission year plus a 5-digit sequence (for example `202600001`). Numbers already in use (including imported records) are skipped.

| Student number token | Meaning |
|---|---|
| `{YYYY}` | Admission year |
| `{YY}` | Last two digits of the admission year |
| `{SEQ:n}` | Sequence padded to n digits. The pattern must contain exactly one. Counted separately per prefix (for example `2026`) |

The student number and status of a record are not changed on the edit page. The status changes through status changes ([chapter 13](13-status-changes-and-advisors.md)).

## Viewing scope for student records

| Permission scope | Student records you can see |
|---|---|
| `View student records` or `Create and edit student records`, All scope | Every student record |
| Org unit scope | Records in that unit and its descendants (for example College of Engineering scope = every department of the college) |
| Program scope | Records in that program |
| Org unit or program scope (second majors and minors) | Records of students following that unit or program as a second major or minor (view only) |
| Second major and minor approver | Records of students who submitted an application to decide (view only) |
| Advisor | Current advisees |
| The student | Their own records |

The same rules exist in the database (row level security), so queries outside the screens (reports, direct connections) cannot exceed the scope either.

## Instructors

With **Add instructor** at the top of the **Instructors** list (the page is titled **New instructor**), choose an existing person or enter a new one (`Manage instructors` permission). Once the end date has passed, the instructor leaves the current instructor list (default filter) and the advisor selector.

## Loading many at once with CSV

Use **Import CSV** at the top of the student record and instructor lists. Column formats are in [chapter 9](09-csv-import.md#students-and-instructors).
