# 4. Audit

The three screens under the **Audit** menu are read-only; nobody can edit or delete them (requires the `View audit records` and `View security events` permissions). The lists have no add, change or delete buttons; opening a row shows its details read-only.

| Screen | What it shows | Examples |
|---|---|---|
| Activity log | Who did what, and **why**. Reason and details | Role assignment (reason: covering during the term), permission change (added/removed list), settings change (before/after), command run |
| Data changes | Before and after values of table rows. Direct changes that bypass the application are recorded too | `users` UPDATE, changed column `locale` |
| Security events | Sign-ins, failed sign-ins, two-factor authentication, permission-related events, password and email changes, audit pruning (`audit_prune`) | Sign-in failed (sign-in name, IP) |

## How to read them

- **User** column: actions taken on screen show the user name or `user:number`, automatic jobs (Celery) show `system:job:...`, commands show `system:command:...`.
- Passwords, two-factor secrets and similar values are masked as `[redacted]`.
- Records with the same **Request ID** were created by one screen request. Searching for the same request ID across the screens shows the full trail of one action. Command runs use a run ID starting with `cmd-`.

## Common lookups

Choose conditions under **Filters** at the top right of a list and type values into the search field.

| What you want to know | How |
|---|---|
| When a user's permissions changed | In the activity log, log `security`, events `role.assigned`, `role.assignment_revoked` |
| An account with many failed sign-ins | In security events, filter by event `Sign-in failed`, see the sign-in name column |
| Who changed the security policy | Activity log event `settings.updated` |
| How a specific row changed | In data changes, filter by table and search by record ID |
