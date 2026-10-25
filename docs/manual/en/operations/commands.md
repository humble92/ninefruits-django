# Management command reference

- Audience: IT operators
- Scope: every command registered by the Ninefruits apps in this repository (`ninefruits/*/management/commands/`) and the Django built-in commands used in operations. When a command is added, a `### \`command\`` entry must also be added to this document (all 4 languages), or CI fails (`tests/tooling/test_command_documentation.py`).

## Common conventions

Every command runs as `uv run manage.py {command}`. In the Docker development environment, `docker compose exec app uv run manage.py {command}`.

| Item | Rule |
|---|---|
| Name | The original `{context}:{action}` becomes `{context}_{action}` (Django command names cannot contain `:`). Example: `term:close` → `term_close` |
| Audit record | Commands that change data ("Audit: recorded" below) write the command, arguments, options, OS user, exit code and result to the activity log (log `command`) on every run. Check them under **Audit > Activity log** in the administration panel |
| Run ID | Every run gets an ID starting with `cmd-` in place of the request ID. The activity log, the data changes made by that run and the Celery tasks it dispatched all carry the same ID, so "which command made this change" is answered by the ID. `--actor` is a value supplied by the operator, so it is not put into the user column of the data changes (the actual actor is the OS user) |
| `--actor=<email>` | Common to all audited commands. Records the responsible administrator account. An unknown email aborts the run |
| `--dry-run` | Prints the result without changing anything. Available on operations that are hard to undo |
| `--force` | Runs without confirmation prompts (for schedules and deployment scripts) |
| `--reason=` | Available on commands that require a reason |
| Exit codes | 0 success, 1 failure or cancelled, 2 a check command found a problem |
| DB context | While the command runs, the DB session actor is set to `system:command:{command}` and appears in the data changes (trigger) |

## Django built-in commands

### `migrate`

- Purpose: applies database migrations. A Ninefruits wrapper around the Django command: without `--database` it uses the schema owner connection (`migrator`, role `app_migrator`). The application connection (`app_runtime`) has no DDL privileges. `showmigrations` and `sqlmigrate` also default to the `migrator` connection.
- When: on first installation and on every deployment (`setup_install` runs it as well).
- Options: the same as Django `migrate` (`app_label`, `migration_name`, `--plan`, `--check`, `--database`).
- Audit: not recorded (schema changes are kept in the migration history `django_migrations`)
- Examples

  ```bash
  uv run manage.py migrate
  uv run manage.py migrate --plan
  ```

- On failure: for permission errors, check the database role preparation (`db/sql/roles/`) in the [installation manual](installation.md).

### `collectstatic`

- Purpose: collects the Vite build output (`static/dist/`) and the Django and unfold static files into `STATIC_ROOT` (`staticfiles/`). The web server (Nginx) serves this directory.
- When: on every deployment, after `npm ci && npm run build`.
- Options: `--noinput` (no prompts), `--clear` (delete existing files before collecting).
- Audit: not recorded
- Examples

  ```bash
  npm ci && npm run build
  uv run manage.py collectstatic --noinput
  ```

### `compilemessages`

- Purpose: compiles the translation files (`.po`) into the runtime `.mo` files. `.mo` files are not kept in the repository, so run this on every installation and deployment. `gettext` must be installed on the system.
- When: on every deployment and after editing translation files.
- Options: `--locale=` (e.g. `ko`, `zh_Hans`, `lo`), `--ignore=.venv`.
- Audit: not recorded
- Examples

  ```bash
  uv run manage.py compilemessages --ignore=.venv
  ```

### `createsuperuser`

- Purpose: **not used.** A Django superuser bypasses the role and permission catalog and the audit trail, so this command ends with an error (exit code 1) and points to `security_create_administrator`.
- Instead: create the first administrator with `security_create_administrator` (includes the system administrator role assignment and an audit record).
- Audit: not applicable

## Installation and demo (Phase 1)

### `setup_install`

- Purpose: new installation and update. Runs, in order: migrations, essential data (role templates and permission sync, countries, languages, code list types, org unit types), institution settings, the grade scale, installation profiles and the first administrator. Safe to run again (existing data and values administrators changed are kept).
- When: on first installation and on every deployment.
- Options: `--institution-name=`, `--locale=` (default language), `--timezone=` (e.g. `Asia/Seoul`), `--profile=` (installation profile key, may be repeated: `korean-university`, `yust-legacy`), `--grade-scale=` (grade scale `4.5` or `4.3`; fixed once set; empty means the first profile's scale), `--admin-email=`, `--admin-name=`, `--force` (no questions; the administrator password is read from standard input).
- Audit: recorded (profiles applied, whether an administrator was created)
- Examples

  ```bash
  uv run manage.py setup_install
  echo "$ADMIN_PASSWORD" | uv run manage.py setup_install --force --locale=ko --timezone=Asia/Seoul \
      --institution-name="Demo University" --profile=korean-university \
      --admin-email=admin@example.ac.kr --admin-name="Administrator"
  ```

- Reading the output: `DONE` per step. `Administrator exists` means a System Administrator assignment exists, so creating one was skipped.
- On failure: a missing key error means `DJANGO_SECRET_KEY` and the values from `pii_generate_key` must be set in the environment. A migration failure: check the database roles ([installation](installation.md)). `The grade scale is fixed` means `--grade-scale` differs from the scale already fixed.

### `setup_demo`

- Purpose: creates a fictional university (org units, programs, buildings and rooms, the last, current and next term around today with their windows, the Korean university profile). Prints the fixed demo accounts per role (`registrar@demo.test` and so on, password `demo-password`). Volumes are created with bulk inserts.
- When: development, training and demonstration environments. **Never runs in production (`DJANGO_ENV=production`), even with `--force`.**
- Options: `--size=tiny|small|medium|large` (about 20/100/2,000/20,000 students; `tiny` for tests and quick checks), `--seed=` (same value, same data), `--force` (no confirmation).
- `--student-accounts`: gives every enrolled student an account and writes `load-accounts.csv` (email, password) in private storage, for load tests ([load testing](load-testing.md)).
- Audit: recorded (size, seed, duration)
- Example: `uv run manage.py setup_demo --size=small --seed=42 --force`
- On failure: without essential data the demo accounts are skipped (their roles are missing); run `setup_install` first. Running again on the same database skips the demo data that exists.

## Reference data and terms (Phase 1)

### `reference_import`

- Purpose: imports reference data from CSV, with the same rules as **Import CSV** in the administration panel (rows are found by code and updated, empty translation cells keep existing values, failed rows are kept separately).
- Arguments: `type` `org_units`, `programs`, `buildings`, `rooms`, `lookup_values`, `students` (student records), `instructors`, `courses` (course versions), `registration_holds` (registration holds) / `file` UTF-8 CSV with a header row.
- Options: `--actor=` (required; the import is recorded under this account and its result appears on that account's **CSV imports** screen), `--chunk=100` (rows per Celery task), `--dry-run` (header check and row count only).
- Audit: recorded (type, file name, rows, import number, failed rows)
- Column format: [administrator manual chapter 9](../admin/09-csv-import.md).
- Exit codes: when the tasks run right away (eager workers), the result is printed and failed rows give 2. When the import is only queued, 0. The result and the failed rows CSV are under **Reference data > CSV imports** in the administration panel.
- Example: `uv run manage.py reference_import org_units /srv/import/org-units.csv --actor=admin@example.ac.kr --dry-run`

### `term_inspect`

- Purpose: shows the terms in session and the open business windows (type, term, session, name, eligibility, closing time) at a point in time. Used to check term and window settings, or questions such as "why is registration not open?".
- Options: `--at=` (default now; e.g. `"2027-02-15 09:00"`; without a time zone the server time zone (UTC) applies; `"2027-02-15 09:00 Asia/Seoul"` or `2027-02-15T09:00+09:00` name one).
- Audit: not recorded (read only)
- Reading the output: dates are judged in the institution time zone. Windows of planned or archived terms never open. Closing times are shown in the institution time zone.

## Security (Phase 0, 2)

### `security_create_administrator`

- Purpose: creates an account with the system administrator role. Usually called by `setup_install`.
- Options: `--email=`, `--name=`, `--password-stdin` (password from standard input. Required for non-interactive runs).
- Audit: recorded (ID of the created user)
- Example: `uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator"`
- Example (non-interactive): `printf '%s\n' "$ADMIN_PASSWORD" | uv run manage.py security_create_administrator --email=admin@example.ac.kr --name="Administrator" --password-stdin`
- On failure: `system_administrator role is missing` means `setup_install` must run first. The password must be at least 12 characters.

### `security_sync_permissions`

- Purpose: aligns the DB permission list with the permission catalog in code. New permissions are created; permissions missing from the catalog are deleted (and removed from every role). System roles always receive every permission.
- When: after deployment (`setup_install` does this as part of the essential data step).
- Options: `--dry-run` (prints only the create/delete list), `--force` (skips the deletion confirmation).
- Audit: recorded (permissions created/deleted)
- Reading the output: `create` and `delete` lines. A confirmation prompt appears when there are deletions.
- On failure: answering "no" to the confirmation exits with code 1 and changes nothing.

### `security_reencrypt_secrets`

- Purpose: after a `DJANGO_SECRET_KEY` rotation, encrypts the secrets protected with a key derived from it (authenticator app TOTP secrets, recovery code seeds, SSO client secrets) again with the new key. Until then they are read with the previous key in `DJANGO_SECRET_KEY_FALLBACKS`. Run it before removing the previous key ([Key management](security-keys.md)).
- Arguments/options: `--dry-run` (only counts the secrets still encrypted with a previous key).
- Audit: recorded (counts)
- Reading the output: `Dry run: 0 authenticator(s) and 0 SSO client secret(s) use a previous key.` means the previous key can be removed. `cannot be decrypted` means a value cannot be read with any configured key: put the previous key in `DJANGO_SECRET_KEY_FALLBACKS` and run again.
- Example: `uv run manage.py security_reencrypt_secrets --dry-run`

### `security_reset_mfa`

- Purpose: resets a user's two-factor authentication (authenticator app, email codes, recovery codes, remembered devices). The user enrolls again at the next sign-in. Use it when no administrator can sign in to the administration panel (for example the only administrator lost their phone). Otherwise use **Users > Reset two-factor authentication** in the administration panel.
- Arguments/options: `{user}` user email, `--reason=` (required), `--actor=` (required. The administrator who decided on the reset).
- Audit: recorded (both in the activity log and the security log, with the reason)
- Example: `uv run manage.py security_reset_mfa admin@example.ac.kr --reason="Phone lost, identity verified by phone call" --actor=it-lead@example.ac.kr`

### `security_unlock_user`

- Purpose: unlocks an account locked by repeated wrong passwords before the lock period ends. Same as **Users > Unlock sign-in** in the administration panel.
- Arguments/options: `{user}` user email, `--reason=` (required).
- Audit: recorded (also in the security log)
- Reading the output: `The account is not locked.` means nothing was changed.
- Note: the lock thresholds (failed attempts, lock duration) are set under **Settings > Sign-in methods** in the administration panel.

## People and student records (Phase 2)

### `people_find_duplicates`

- Purpose: lists people who appear to be the same person. The criteria are an identical national ID number (search hash), or an identical romanized name and date of birth. Merged people are excluded.
- Options: `--limit=100` (number of groups to print).
- Audit: not recorded (read only)
- Exit codes: 2 when duplicate candidates exist.
- Follow-up: review each group under **People** in the administration panel and, if they are the same person, run **Merge duplicate** from the page of the person to keep. A merge cannot be undone ([Administrator manual chapter 14](../admin/14-merge-and-invitations.md)).
- Example: `uv run manage.py people_find_duplicates --limit=50`

## Admissions (Phase 3)

### `admission_matriculate`

- Purpose: creates student records (new student numbers) for the confirmed applicants of an admission cycle. Same as the bulk **Create student record** on **Admissions > Applications** in the administration panel (`MatriculateApplicant`). Each applicant is processed on its own, so one failure does not stop the rest.
- Arguments/options: `cycle` admission cycle code, `--term=` (required; admission term code, e.g. `2027-SP`; the admission date is the term's first day), `--actor=` (required; an account with `Create student records for admitted applicants`; only applicants in that account's scope are processed), `--dry-run` (list only).
- Audit: recorded (cycle, term, candidates, created, failed application numbers). Each applicant also gets a business audit entry (`application.matriculated`).
- Exit codes: 1 when the cycle or term code is unknown or `--actor` is missing, 2 when an applicant failed.
- Example: `uv run manage.py admission_matriculate DEMO-2027-REG --term=2027-SP --actor=admissions@example.ac.kr --dry-run`
- On failure: `Only accepted offers without a student record ...` means the applicant already has a record or has not confirmed; `The program is not in effect on the admission date.` means the program is not valid on the admission date (check the program's validity under Reference data > Programs); `not in your scope` means the application is outside the `--actor` account's scope.

### `admission_expire_drafts`

- Purpose: marks as **Expired** the draft applications of closed cycles and the drafts not changed for the configured period (**Settings > Admissions > Expire untouched drafts after (days)**, default 90). Expired applications no longer block a new application to the same cycle.
- When: scheduled daily at 03:10 (the Celery beat task `admission.expire_drafts` runs this command).
- Options: `--dry-run` (count only).
- Audit: recorded (number expired)
- Example: `uv run manage.py admission_expire_drafts --dry-run`

## Course sections (Phase 4)

### `section_copy`

- Purpose: starts the planning of a new term from the sections of a previous term. Same as **Sections > Copy from another term** in the administration panel (`CopySections`). Copies the sections that were not cancelled as drafts, together with the instructors (if still employed), meeting times and rooms, seat allocations (release times shifted by the difference between term start dates) and the syllabus (as a private draft). The course version is replaced by the version in effect at the start of the new session.
- Arguments/options: `from-term`, `to-term` term codes (for example `2026-FA`), `--org-unit=` (only sections of this org unit code; repeatable), `--dry-run` (does the copy in a transaction and rolls it back, so the report is exact), `--actor=` (required. Only sections within that account's `Plan sections` permission scope are copied).
- Audit: recorded (source and target term, copied, skipped and needs-review counts; a real copy also records the business audit event `sections.copied`)
- Reading the output: `skipped` means the target term already has the same section code or there is no course version in effect; `note` means the section was copied but something was left out (copied without a room because the room is already taken, a retired instructor, and so on). Sessions are matched by code; if there is none, the section goes into the full-term session.
- Exit codes: 1 for an unknown term code or a missing `--actor`.
- Example: `uv run manage.py section_copy 2026-FA 2027-FA --actor=academic@example.ac.kr --dry-run`

### `schedule_check_conflicts`

- Purpose: checks the sections of a term before publishing the timetable. Double booking of rooms and instructors is already prevented by the DB; this finds the problems the DB allows: capacity above the room capacity, a course version not in effect at the session start date, a retired instructor, seat allocations above capacity, meeting dates outside the session. It also checks room conflicts in data that came in without constraints, such as a backup restore.
- Arguments: `term` term code.
- Audit: not recorded (read only)
- Exit codes: 2 when problems exist, 1 for an unknown term code. Sections that have no instructor, room or meeting time yet are shown for information only (`Note`).
- Example: `uv run manage.py schedule_check_conflicts 2027-SP`

## Registration (Phase 5)

### `registration_preflight`

- Purpose: checks a term before opening registration. Shows the registration and add/drop windows, the rule set, the number of published sections, sections with capacity 0, seat allocations above capacity, course versions not in effect at the session start date, the number of active students not covered by a credit limit, and the number of students with a registration hold.
- Arguments: `term` term code (for example `2027-SP`).
- Audit: not recorded (read only)
- Exit codes: 2 when problems exist. A missing rule set is shown for information, not as a problem (rule defaults apply).
- Example: `uv run manage.py registration_preflight 2027-SP`

### `registration_simulate`

- Purpose: shows, rule by rule, what would happen if the student registered for the section now (or at a given time). Nothing is saved and no attempt is recorded. Use it for "why can I not register?" questions.
- Arguments: `student-number` student number, `section` `course code-section code` (for example `CSE2010-01`).
- Options: `--term=` (term code. Default is the most recent term that has that section), `--at=` (time of evaluation. For example `"2027-02-10 10:00 Asia/Seoul"`).
- Audit: not recorded (read only)
- Reading the output: per rule, pass/fail, block/warn and the message. A rule covered by an override shows as failed but does not block. Capacity is shown separately below the rule table.
- Exit codes: 2 when the registration would be refused.
- Example: `uv run manage.py registration_simulate 202612345 CSE2010-01 --at="2027-02-10 10:00 Asia/Seoul"`

### `waitlist_promote`

- Purpose: registers waitlisted students in order for sections that have free seats. Every rule is checked again at promotion; waitlist entries that fail a rule are removed from the waitlist (with the reason recorded). Waitlists of sections whose registration and add/drop windows are both closed expire. Students receive the result by email.
- Arguments/options: `term?` term code (default: every term with waitlist entries), `--actor=`.
- Audit: recorded (sections, promoted, removed, expired counts)
- When: on a drop, a withdrawal or a seat allocation release, the affected section is processed immediately by a queue job. This command is the hourly scheduled safety net that handles anything that was missed.
- Example: `uv run manage.py waitlist_promote 2027-SP --actor=registrar@example.ac.kr`

### `registration_release_reserved_seats`

- Purpose: marks seat allocations whose release time has passed (for example seats reserved for majors) as processed and queues the waitlist promotion job for those sections. Reserved seats become general seats in the calculation as soon as the release time passes, so this command only hands the seats over to the waitlist.
- Audit: not recorded (runs every 5 minutes. Promotion results are in the registration records)
- When: scheduled (every 5 minutes, Celery beat task `registration.release_reserved_seats`). The promotion task is `registration.promote_waitlist` per section (one at a time per section through a Redis lock).
- Example: `uv run manage.py registration_release_reserved_seats`

## Grades (Phase 6)

### `term_close`

- Purpose: closes a term. Every grade in the term must be finalized. For each chunk of students (100) it calculates the term record (credits, term and cumulative GPA) and determines the academic standing (good standing, academic warning, dismissal review) and honors eligibility (the `grading.close_term_records` tasks of a Celery chord); the finishing task `grading.finish_term_close` then ranks honors per program, closes the term records as official records and sets the term to **Grades closed**. Progress is kept in `job_batches` and shown above the **Grades > Term records** list. When it finishes, the staff member who started it gets an email. Same as **Grades > Term records > Close term** in the administration panel.
- Arguments/options: `term` term code, `--dry-run` (only checks whether the term can be closed), `--reason=` (reason kept in the record), `--actor=`.
- Audit: recorded (number of students, number of sections with unfinalized grades, batch id). When the close finishes, the `term.closed` audit record holds the counts of academic warnings, dismissal reviews and honors.
- Exit codes: 2 when some sections have unfinalized grades (the unfinalized count per section is printed). 1 when the term is not in published status.
- When: after grade entry and finalization are complete. Follow the batch in Flower and on the term records screen. Without a Celery worker the term status does not change. A chunk that fails with a database error is retried up to 3 times; if it still fails, the batch stays failed and the term does not change (fix the cause and run it again; running again gives the same result).
- Examples: `uv run manage.py term_close 2026-FA --dry-run`, `uv run manage.py term_close 2026-FA --reason="Fall 2026 grades closed" --actor=registrar@example.ac.kr`

### `grades_recalculate`

- Purpose: recalculates term records (credits, term and cumulative GPA) from finalized grades. Use it to apply a changed grading policy (GPA decimal places, retake handling) to past terms. Academic standing and honors keep the values decided at term close. An approved grade change recalculates that student automatically, so this command is not needed for it.
- Options: `--term=` (students with grades in that term, from that term onwards), `--student-number=` (one student), `--reason=` (required), `--actor=`.
- Audit: recorded (number of students, reason)
- Exit codes: 1 without a reason, or for an unknown term code or student number.
- Example: `uv run manage.py grades_recalculate --term=2026-SP --reason="GPA changed to three decimal places"`

### `grades_remind_missing`

- Purpose: emails the instructors of sections whose grades have not been submitted yet (not entered or saved as draft). Sections are grouped per instructor into one message each.
- Arguments/options: `term` term code, `--dry-run` (prints the targets without sending), `--actor=`.
- Audit: recorded (sections, instructors, messages sent)
- When: a few days before the grade entry window closes. Add it to the schedule if needed.
- Example: `uv run manage.py grades_remind_missing 2026-FA --dry-run`

## Course evaluation (Phase 7)

### `evaluation_remind`

- Purpose: emails students who still have unevaluated courses while the course evaluation window is open. The remaining courses are grouped per student into one message (in the recipient's language).
- Arguments/options: `term` term code, `--dry-run` (number of target students only, nothing sent), `--actor=`.
- Audit: recorded (target students, messages sent)
- Exit codes: 1 for an unknown term code.
- When: once or twice during the evaluation window. Add it to the schedule if needed.
- Example: `uv run manage.py evaluation_remind 2026-FA --dry-run`

### `evaluation_publish_results`

- Purpose: publishes the term's course evaluation results to instructors. Same as **Course evaluation > Term evaluations > Publish results** in the administration panel. Even after publication, results are visible only for sections that reached the minimum number of responses and the response rate.
- Arguments/options: `term` term code, `--actor=` (an account with `Manage evaluation forms, term evaluations and publication`; recorded as the publisher).
- Audit: recorded (number of responses, whether already published). Business audit `evaluation.published`.
- Exit codes: 1 for an unknown term code or a term without a course evaluation.
- When: after the evaluation window and grade processing are complete. A term already published is not changed.
- Example: `uv run manage.py evaluation_publish_results 2026-FA --actor=academic-affairs@example.ac.kr`

## Certificates (Phase 8)

### `certificate_verify`

- Purpose: checks a certificate verification code with the same criteria as the public verification page. Prints the kind, serial number, issue date and the masked holder.
- Arguments/options: `code` verification code (case does not matter).
- Audit: none (read only)
- Exit codes: 0 when valid, 2 for an unknown code, a revoked certificate or an expired validity period.
- Example: `uv run manage.py certificate_verify 7Q2M9XK4TB0RWZ5C1HNA`

### `certificate_render`

- Purpose: renders the PDF of an issued certificate again with the current data and template, replacing the stored file. Same as **Certificates > Issued certificates > Render again** in the administration panel. The serial number and verification code stay the same; the checksum changes. The PDF is made by Gotenberg.
- Arguments/options: `issue` serial number, `--reason=` (required), `--actor=` (an account with `Issue, re-render and revoke certificates`).
- Audit: recorded (serial number, new checksum); business audit `certificate.rerendered`.
- Exit codes: 1 without a reason, for an unknown serial number, or when the PDF cannot be made.
- When: to regenerate a specific certificate after fixing a template, a name spelling or `APP_URL`.
- Example: `uv run manage.py certificate_render ENR-2026-000001 --reason="Name spelling corrected"`

## Examinations (Phase 9)

### `assessment_import_results`

- Purpose: enters the results of an examination session from CSV. Same rules as **Examination sessions > Import results (CSV)** in the administration panel (registered students only, pass decided from the scores, entering again before publication replaces the result, after publication the rows are reported as errors).
- Arguments/options: `type` examination kind code / `held_date` examination date `YYYY-MM-DD` / `file` a UTF-8 CSV with a header row, `--actor=` (required, recorded as the person who entered the results), `--dry-run` (row validation only, nothing recorded).
- Column format: [Administrator manual chapter 24](../admin/24-assessments.md).
- Audit: recorded (session, file name, row count, entered/absent/error counts). Each result also gets the business audit entry `assessment.result_recorded`.
- Exit codes: 1 when the session is not found, the file cannot be read or `--actor` is missing; 2 when there are error rows (the other rows are recorded).
- Example: `uv run manage.py assessment_import_results ENG_COMP 2026-05-15 storage/eng.csv --actor=registrar@example.ac.kr --dry-run`

### `assessment_publish_results`

- Purpose: publishes a session's results to students. Same as **Examination sessions > Publish results** in the administration panel. After publication results change only through correction requests.
- Arguments/options: `type` examination kind code / `held_date` examination date, `--actor=` (required, with the permission to register students, enter and publish results).
- Audit: recorded (session, number of results) and the business audit entry `assessment.results_published`
- Exit codes: 1 when the session is not found, is already published, `--actor` is missing or lacks the permission.
- When: after result entry is complete.
- Example: `uv run manage.py assessment_publish_results ENG_COMP 2026-05-15 --actor=registrar@example.ac.kr`

## Attendance (Phase 10)

### `attendance_generate_sessions`

- Purpose: creates class meetings for every section of a term from its meeting times (weekday, time, period). Same as **Generate from meeting times** in the instructor portal and **Generate meetings** on the **Class meetings** tab of the administration panel. Existing meetings and their attendance are kept (safe to run again). Cancelled sections are skipped.
- Arguments/options: `term` term code, `--section=` (course code-section code, for example `CSE2010-01`, one only), `--dry-run` (number of target sections only), `--actor=`.
- Audit: recorded (term, sections, meetings created)
- When: before the term starts, after meeting times are confirmed. Run again when meeting times change.
- Example: `uv run manage.py attendance_generate_sessions 2026-FA --dry-run`

## Graduation (Phase 11)

### `degree_audit_run`

- Purpose: saves a graduation requirement audit for every enrolled student. Same as **Degree audits > Run audits** in the administration panel. The latest saved audit is the basis for graduation processing. Every run adds new snapshots.
- Options: `--term=` (term code the audit belongs to), `--student-number=` (one student), `--min-year-level=` (only this year level and above), `--actor=`.
- Audit: recorded (number of students, number satisfied). With `--actor` the business audit `graduation.audits_run` is recorded as well.
- Exit codes: 1 for an unknown term code.
- When: before graduation review (end of term), and after changing requirement sets or equivalent courses.
- Example: `uv run manage.py degree_audit_run --term=2026-FA --min-year-level=4 --actor=registrar@example.edu`

## LMS integration (Phase 12)

### `lms_sync`

- Purpose: pushes published sections to the platform (course creation and linking, instructors, enrolled students). Does for a whole term what **Course links > Synchronize again** does in the administration panel. Sections already linked are only re-ensured (idempotent). Every step is kept in the **Sync logs**.
- Arguments/options: `{platform}` platform code, `--term=` (term code, default every term that has not ended), `--section=` (one course code-section code, for example `CSE2010-01`), `--dry-run` (only records what would be sent as "skipped"), `--actor=`.
- Audit: recorded (platform, sections, members, failures)
- Exit codes: 1 for an unknown platform or term code, 2 when any section failed (the error per section is printed).
- When: before the term starts, after a new platform is made active.
- Example: `uv run manage.py lms_sync DEMO --term=2026-FA --dry-run`

### `lms_reconcile`

- Purpose: compares the platform's course rosters with the enrollment lists in the student information system, adds missing members and removes extra ones. Sections not linked yet are synchronized whole. Differences are kept in the sync log (`reconcile`, `missing` and `extra` in the `payload`).
- Arguments/options: `{platform?}` (every active platform if omitted), `--term=` (default the terms that have not ended), `--dry-run` (records differences only), `--actor=`.
- Audit: recorded (sections per platform, added/removed/failed counts)
- Exit codes: 1 for an unknown platform or term code or when no platform is active, 2 when any section failed.
- When: scheduled daily at 02:30 as the task `lms.reconcile` (Celery beat). Run manually after a platform outage.

### `api_issue_token`

- Purpose: issues an API integration token for an account ([ADR 0004-django](../../../../porting/decisions/0004-django-api-tokens.md)), usually a service account with only the permissions it needs (LMS: `lms.manage`, BI: `reports.view`). The token is printed **once**, on the first line of standard output; the database keeps only its digest. Requests send it in the header `Authorization: Token <token>`.
- Arguments/options: `{email}` account email, `--days=` (lifetime 1 to 365 days, default `API_TOKEN_TTL_DAYS` = 90), `--reason=` (what it is for, recorded in the audit), `--actor=`.
- Audit: recorded (`api.token_issued`: key prefix and expiry; never the token itself)
- Exit codes: 1 for an unknown or inactive account or a lifetime out of range.
- Example: `uv run manage.py api_issue_token moodle-sync@example.ac.kr --days=365 --reason="Moodle callbacks" --actor=admin@example.ac.kr`

### `api_revoke_tokens`

- Purpose: revokes an account's API tokens (all, or one with `--key=`). `--list` only lists the tokens (key prefix, issue and expiry times).
- Arguments/options: `{email}`, `--key=` (key prefix), `--list`, `--reason=`, `--actor=`.
- Audit: recorded (`api.token_revoked`: the key prefixes revoked)
- Exit codes: 1 for an unknown account or no token with the `--key`.
- When: when an integration ends, a token may have leaked, or the person in charge changes.

## Operational checks and cleanup (Phase 13)

### `system_health_check`

- Purpose: checks configuration and keys (`DJANGO_SECRET_KEY`, PII keys, `DEBUG`), the DB connection and roles (runtime, migrator, reporting), RLS on personal data tables, pending migrations, permission catalog sync, Redis, the Celery workers, Gotenberg, private storage writes and the beat heartbeat (`core.heartbeat`, within 5 minutes).
- Options: `--json` (output for monitoring).
- Audit: none (read only)
- Exit codes: 2 when any check fails.
- When: right after deployment, when an outage is suspected, periodically from monitoring. Load balancers use `/api/v1/health/`.
- Example

  ```bash
  uv run manage.py system_health_check
  uv run manage.py system_health_check --json
  ```

### `audit_seal`

- Purpose: links new rows of the audit tables (`audit.record_changes`, `audit.activity_log`, `audit.security_events`) into the hash chain ([Audit integrity](audit-and-maintenance.md)). Runs on the schema owner connection (`migrator`).
- Options: `--table=` (one of record_changes, activity_log, security_events; repeatable), `--actor=`.
- Audit: recorded (rows sealed per table)
- When: scheduled daily at 03:30.
- Example

  ```bash
  uv run manage.py audit_seal
  uv run manage.py audit_seal --table=activity_log
  ```

### `audit_verify_chain`

- Purpose: recomputes the content hashes and the chain of the audit rows to find tampering, deletions and reordering. Prints, per table, the rows checked, rows sealed, mismatches and the first mismatching id.
- Options: `--table=`.
- Audit: none (read only)
- Exit codes: 2 when there is a mismatch.
- When: before backups, during security reviews, after pruning.

### `audit_prune`

- Purpose: deletes **sealed** audit rows past their retention period. Runs on the schema owner connection in a transaction with `app.audit_maintenance = on`. Unsealed rows are kept (run `audit_seal` first). Every deletion records the security event `audit.pruned` (table, cutoff date, rows deleted, id range, `chain_hash` of the boundary row).
- Options: `--before=YYYY-MM-DD` (required; rows before midnight of that day), `--table=`, `--dry-run` (counts only), `--actor=`.
- Audit: recorded (cutoff date, rows deleted and id range per table)
- When: according to the retention policy, after a backup.
- Example

  ```bash
  uv run manage.py audit_prune --before=2023-03-01 --dry-run
  uv run manage.py audit_prune --before=2023-03-01 --table=record_changes --actor=ops@example.edu
  ```

### `media_prune_orphans`

- Purpose: deletes media rows whose owner no longer exists and directories (`<media id>/`) on the private storage without a row (person photos, application documents, certificate PDFs, examination evidence).
- Options: `--dry-run` (list only), `--actor=`.
- Audit: recorded (rows, directories)
- When: monthly or after a bulk deletion.

## Personal data encryption keys (Phase 0)

### `pii_generate_key`

- Purpose: prints new keys (32 bytes, `base64:...`) for `PII_ENCRYPTION_KEY` and `PII_HASH_KEY`. Saves nothing.
- Audit: not recorded
- Caution: changing `PII_HASH_KEY` invalidates every search hash (`*_hash`). Rotate only the encryption key: move the old key to `PII_PREVIOUS_KEYS`, then run `pii_reencrypt`.
- Example

  ```bash
  uv run manage.py pii_generate_key
  ```

### `pii_reencrypt`

- Purpose: after a key rotation, re-encrypts personal data encrypted with a previous key using the current key. Runs as a group of Celery tasks over chunks of records. Records already on the current key are left alone.
- Arguments: the model with encrypted personal data fields (`app_label.Model`, e.g. `person.Person`).
- Options: `--chunk=500` (records per task), `--dry-run` (only counts records using a previous key), `--force` (no confirmation), `--actor=`.
- Audit: recorded (batch ID, number of tasks / preview count)
- Verification: follow the tasks in Flower. When they finish and `--dry-run` reports 0, remove the previous key from `PII_PREVIOUS_KEYS`.
- Example

  ```bash
  uv run manage.py pii_reencrypt person.Person --dry-run
  uv run manage.py pii_reencrypt person.Person --force --actor=ops@example.edu
  ```

## Localization (Phase 0)

### `i18n_missing`

- Purpose: extracts the translatable strings from the source the way `makemessages` does (without writing files), compares them with every catalog (global `locale/` and each app's `locale/`) and lists, per language, missing strings (not in the catalog, empty `msgstr`, fuzzy, placeholders that differ) and obsolete entries.
- Arguments/options: `[locale]` (one language only, e.g. `ko`, `zh-hans`, `lo`), `--strict` (exit code 2 when strings are missing; used in CI), `--no-extract` (check the catalogs only, no source scan).
- Audit: not recorded
- Requires: GNU gettext (`xgettext`, `msguniq`).
- Example

  ```bash
  uv run manage.py i18n_missing --strict
  uv run manage.py i18n_missing lo
  ```

### `i18n_export`

- Purpose: writes a sheet for translators (`.xlsx` or `.csv`, chosen by the extension). Columns: `catalog` (catalog location), `context`, `source` (English msgid), `source_plural`, `translation`, `note` (original key).
- Arguments/options: `{locale} {path}`, `--missing` (only strings without a translation).
- Audit: not recorded
- Example: `uv run manage.py i18n_export ko storage/ko.xlsx --missing`

### `i18n_import`

- Purpose: writes a sheet filled by translators back into the catalogs (`.po`) and compiles them (`.mo`). Only strings that exist in the catalogs (same catalog, context and English text) are imported; empty translations are skipped.
- Arguments/options: `{locale} {path}`, `--dry-run` (list the strings that would be written), `--actor=`.
- Audit: recorded (language, number of translations)
- Note: the catalogs live in the repository. Commit the `.po` changes after an import.

### `i18n_makemessages`

- Purpose: runs `makemessages` from the repository root so every catalog matches the source (ko, zh_Hans, lo). Strings go to the app's `locale/` when the app has one, otherwise to the global `locale/`. `.venv`, `tests`, `docs` and similar directories are skipped.
- Options: as Django `makemessages` (`-l`, `--no-obsolete`, ...).
- Audit: not recorded
- Example: `uv run manage.py i18n_makemessages`

## Checks (Phase 0)

### `pdf_sample`

- Purpose: renders a table mixing Korean, Chinese, Lao and English to PDF to check the fonts and the connection to the PDF service (Gotenberg).
- Argument: `[path]` (default `pdf-sample.pdf`, relative to the private file storage `PRIVATE_MEDIA_ROOT`).
- Audit: not recorded
- On failure: exit code 1. For connection errors check `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` and the Gotenberg container.
- Example: `uv run manage.py pdf_sample`

### `naming_check`

- Purpose: checks the database schema and the sources against the [naming conventions](../../../development/naming.md). It checks the table and column names in the actual database catalog (schemas `public`, `audit`, `reporting`), the migration file names of the Ninefruits apps, management command names (`context_action`) and the msgids and msgctxts of the translation catalogs (`.po`).
- Rules: snake_case, forbidden suffixes (`_old`, `_new`, `_backup`, `_tmp`, dates, numbers), names containing a language code, time columns without time zone (`timestamp without time zone`), boolean column names (`is_`, `has_`, `can_` or a verb), date column names (`_date`), msgids shaped like semantic keys (`registration.errors.x`). Tables defined by Django and packages (`django_*`, allauth, Celery beat, `settings`, `cache`, `jobs`, `media` and so on) are excluded.
- Options: `--database=` (database connection to check, default `default`), `--skip-database` (file checks only, no database).
- Audit: not recorded
- Exit code: 2 when problems are found.
- Example

  ```bash
  uv run manage.py naming_check
  ```
