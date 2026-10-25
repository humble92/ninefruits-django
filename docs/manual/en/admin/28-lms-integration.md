# 28. LMS Integration

Menu: administration panel **LMS integration > LMS platforms**, **Course links**, **Sync logs** (`Manage LMS platforms, links and synchronization` permission; default: System Administrator, Academic Affairs). Instructors use the LMS links under the portal **My teaching** and in the section detail, and **Load scores from the LMS** on the grade entry screen. Loading follows the same conditions as grade entry (the assigned instructor, within the grade entry window).

Developer details (writing a connector, the API) are in the [LMS integration guide](../../../lms-integration-guide.md).

## What goes where

| SIS → LMS | When |
|---|---|
| Section (course creation) + instructors | When the section is **published**, and with `lms_sync` |
| Confirmed registration → enrollment | Immediately on registration, waitlist promotion or staff registration |
| Drop or withdrawal → unenrollment | Immediately |
| Full reconcile | Daily at 02:30 (`lms_reconcile`, scheduled task `lms.reconcile`) |

| LMS → SIS | When |
|---|---|
| Final scores (draft) | When the instructor clicks **Load scores from the LMS** on the grade entry screen. Saving and submitting is done by the instructor |

Finalized grades are not sent to the LMS. Course materials, assignments and quizzes live in the LMS.

## Platforms

**LMS platforms**: code, name (per language), driver, base URL, credentials, active, synchronize rosters, pull final scores.

- Driver **None (records only)**: calls nothing and records what would be sent. Use it to check the flow or for demonstrations before integrating. The `DEMO` platform in the demo data uses it.
- `Moodle`, `Open edX`: no connector yet (marked "not implemented yet"). When chosen, synchronizations are recorded as failed.
- Turning **Active** on makes section publications and registration changes flow immediately from then on and includes the platform in the nightly reconcile.
- **Credentials** are written one `key=value` per line (e.g. `token=...`). They are stored encrypted and never shown back. Leaving the field empty on edit keeps the stored values. The data change history does not hold the values either.

## Course links and sync logs

- **Course links**: which section is linked to which platform course (id, URL), status (Pending/Linked/Failed), last synchronization and error. Filters for platform, status and term; search by course code. The row action **Synchronize again** (with a confirmation page) pushes the section, instructors and roster again.
- **Sync logs**: result and message per step (course, add and remove member, pull scores, scores delivered, reconcile). Look here for the cause of a failure. Opening a row shows the start and finish times and the payload.
- Commands: `uv run manage.py lms_sync {platform} --term={term}` (full push, `--dry-run`), `uv run manage.py lms_reconcile` (reconcile). See [operations commands](../operations/commands.md#lms-integration-phase-12).

## Portal

- The platform course link is shown in the course detail for students and instructors and in the instructor's **My teaching** list (**LMS** column; linked sections only).
- Grade entry: when **Pull final scores** is on for the platform and the section is linked, the **Load scores from the LMS** button appears. It only fills the score column and does not save.

## Integration API

An API (`/api/v1/lms/platforms/...`) serves platforms that report results later or send their scores themselves. Create a separate integration account with only the `Manage LMS platforms, links and synchronization` permission; an operator issues its token with `uv run manage.py api_issue_token {email} --days=365` and hands it to the platform's administrator. The token is shown only once, when it is issued. `api_revoke_tokens` revokes it. Issuing and revoking are recorded in the audit log.

- Scores received through score delivery (`.../scores/`) are not saved either. When the instructor clicks **Load scores from the LMS**, the latest scores received fill the form as a draft.
- Sync results (`.../sync-results/`) are kept in the **Sync logs**, and course results change the status in **Course links**.

## Frequently asked questions

- **A student is missing in the LMS.** The student needs an account (user) to be synchronized. Without one, invite them ([chapter 14](14-merge-and-invitations.md)); the next reconcile adds them.
- **A synchronization stays failed.** Read the message in the sync log. Expired credentials are common. Change the values in the platform's edit screen and **Synchronize again**.
- **We switched platforms.** Create the new platform and turn the old one's Active off. Links are created separately per platform.

## Screens in this installation

The screens and features are those of the original (Filament, Livewire); some interactions differ.

- Credentials are entered as `key=value` lines in a text field instead of the original's key/value table. Malformed lines are refused with their line number.
- A platform's **options** (role ids per platform and the like) have no field on screen. Developers set them when a connector needs them ([integration guide](../../../lms-integration-guide.md) section 3).
- **Synchronize again** goes through a confirmation page. Connector errors (a driver without a connector, a platform outage) show as the message "Synchronization failed: ..." and the course link becomes Failed (the original showed an error page).
- Sync logs are read only. Opening a row shows the payload as JSON.
- **Load scores from the LMS** on the grade entry screen is in the button row under the table. It shows the page again with only the score fields changed, keeping what was already typed. Nothing is saved until **Save draft**.
- The integration API and the token commands (`api_issue_token`, `api_revoke_tokens`) are new in this installation (the original had no API).

[Administrator manual contents](README.md)
