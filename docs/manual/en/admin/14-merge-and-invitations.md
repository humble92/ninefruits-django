# 14. Merging people and account invitations

Menu: **Students and staff > People**, then **Merge duplicate** and **Invite to create an account** at the top of a person's detail page

## Merging duplicate people

Used when the same human being was registered as two people (for example a readmission where the existing person was not found and a new one was created). Requires the `Merge duplicate people` permission.

1. Find candidates: search the people list for the same name and birth date, or the same national ID number. The IT operator can produce a full candidate list with `uv run manage.py people_find_duplicates`.
2. On the detail page of the **person to remove (the duplicate)**, press **Merge duplicate**, choose the person under **Keep this person** from the list, and enter a reason. When the merge finishes, you are taken to the kept person's page.
3. The removed person's student records, applications, instructor details, guardians and account move to the kept person. If both have an account, the removed person's account is deactivated and its linked school sign-in is moved where possible.
4. The removed person stays as **Merged** (list filter **Merged**) so old records can still be found. It cannot be used for new student records.

- If both people have instructor details, the merge is refused. Tidy up the instructor details first.
- If both people have an open application in the same admission cycle, the merge is refused. Ask the applicant to withdraw one.
- **This cannot be undone.** Always check the student records and birth date before merging. The merge is written to the activity log with its reason.

## Account invitations

Sends an invitation email to people without an account, such as students and instructors loaded by CSV. Requires the `Invite people to create an account` permission.

1. On the person's detail page, press **Invite to create an account** and enter the sign-in email (usually a personal email).
2. When the recipient chooses a password through the link in the email, the account is created and they are signed in immediately.

- The link is valid for **Settings > Student records > Invitation links valid for (days)** (default 14 days).
- Sending again invalidates the previous link.
- You cannot invite a person who already has an account, or use an email that another account uses.
- The same account is kept after graduation. Ask people who only used their school email to change their sign-in email to a personal address ([chapter 15](15-sign-in-methods.md)).
