# Audit integrity and routine maintenance

- Audience: IT operators, security officers
- Related: [administrator manual chapter 4, audit](../admin/04-audit.md), [command reference](commands.md), [backup and restore](backup-restore.md)

## Audit hash chain

The audit tables (`audit.record_changes` for data changes, `audit.activity_log` for business activity, `audit.security_events` for security events) are append-only (enforced by triggers). On top of that there is a mechanism that **exposes** tampering.

- Every row gets a SHA-256 of its content (`row_hash`) when it is inserted.
- `audit_seal` (scheduled job `audit.seal`, daily at 03:30) links new rows into the chain in ID order: `chain_hash = SHA-256(previous chain_hash || row_hash)`. It calls the DB function `audit.seal()` over the schema owner connection (`migrator`).
- `audit_verify_chain` recomputes the content hash and the chain of every row. Per table it prints the rows checked, rows sealed, mismatches and the first mismatching id; a row whose content changed is reported as "row mismatch", a missing or reordered row as "chain mismatch", and the command returns exit code 2.

```bash
uv run manage.py audit_seal
uv run manage.py audit_verify_chain
uv run manage.py audit_verify_chain --table=security_events
```

Things to keep in mind

- A row changed before it was sealed (within the same day) cannot be caught by the chain. That is why sealing runs daily and verification runs before backups and during security reviews.
- When pruning (`audit_prune`) removes the oldest rows, the link of the first remaining row is not checked (the pruned range is kept in the prune command's audit record).
- Only the DB administrator (the schema owner `app_migrator`) can set `app.audit_maintenance = on`. The application role (`app_runtime`) has no UPDATE or DELETE privilege on the audit tables.

## Retention and pruning

1. Decide the retention periods (for example data changes 3 years, business activity 5 years, security events 1 year).
2. Take a backup before pruning ([backup and restore](backup-restore.md)) and confirm the chain is intact with `audit_verify_chain`.
3. Check the counts with `uv run manage.py audit_prune --before=YYYY-MM-DD --table=record_changes --dry-run`, then run it without `--dry-run` (record the operator's account with `--actor=`). Unsealed rows are never deleted, so run `audit_seal` first.
4. Run `audit_verify_chain` again after pruning.

The pruning itself is recorded: every run writes to the activity log (log `command`) the cutoff date, options, actor and OS user, plus per table the **number of rows deleted, the range of deleted IDs and the chain_hash at the boundary**; an actual deletion is also recorded as the security event `audit.pruned` (**Audit > Security events**). This record row is itself linked into the chain at the next sealing. This boundary is exactly why `audit_verify_chain` does not check the link of the first remaining row; comparing the boundary hash with the prune record lets you confirm that the deleted range matches a recorded prune.

## File cleanup

`uv run manage.py media_prune_orphans --dry-run` lists media rows whose owner no longer exists and directories without a row (`PRIVATE_MEDIA_ROOT/<media id>/`); without `--dry-run` it deletes them. It covers person photos, application documents, certificate PDFs and examination evidence. Run it monthly or after a bulk deletion.

## Health checks

| Check | How | When it fails |
|---|---|---|
| Service status | `GET /api/v1/health/` (no sign-in, for load balancers and monitoring) | `unavailable` (503) when the DB or the cache does not answer, `degraded` (200) when the scheduler heartbeat is more than 5 minutes old, otherwise `ok`. Signed in with the `Open the administration panel` permission, it also shows each check (`database`, `cache`, `scheduler`) |
| Full check | `uv run manage.py system_health_check [--json]` | 12 checks: keys, DB roles, RLS, migrations, permission catalog, Redis, Celery workers, Gotenberg, storage, beat heartbeat. Exit code 2 when any fails |
| Production settings | `uv run manage.py check --deploy` | Warnings about `DEBUG`, HTTPS redirects, HSTS, secure cookies, the secret key |
| Migrations | `uv run manage.py migrate --check` | Exit code 1 when migrations are unapplied |
| Permission catalog | `uv run manage.py security_sync_permissions` | Brings the code's permission list into the DB (safe to run again) |
| PDF service | `uv run manage.py pdf_sample` | Gotenberg connection, fonts |
| Translations | `uv run manage.py i18n_missing --strict` | Exit code 2 when translations are missing |
| Audit chain | `uv run manage.py audit_verify_chain` | Exit code 2 on a mismatch |
| Queue | Flower, `uv run celery -A config inspect ping` | The worker does not answer |

Connect monitoring to the HTTP status and the `status` value of `/api/v1/health/`; run the others at deployment and in the [routine checks](deployment-checklist.md#routine-checks).
