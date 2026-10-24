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
- When: on first installation and on every deployment (from later phases on, `setup_install` runs it as well).
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

## Reference data and terms (Phase 1)

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

## Admissions (Phase 3)

## Course sections (Phase 4)

## Registration (Phase 5)

## Grades (Phase 6)

## Course evaluation (Phase 7)

## Certificates (Phase 8)

## Examinations (Phase 9)

## Attendance (Phase 10)

## Graduation (Phase 11)

## LMS integration (Phase 12)

## Operational checks and cleanup (Phase 13)

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
