# Backup and restore

- Audience: IT operators
- Related: [installation](installation.md), [key management](security-keys.md), [audit integrity](audit-and-maintenance.md)

## What to back up

| Target | Method | Frequency (recommended) |
|---|---|---|
| PostgreSQL | `pg_dump -Fc` or PITR (WAL archiving) | Daily full + continuous WAL |
| Private file storage (`PRIVATE_MEDIA_ROOT`, default `storage/private`) | Snapshot or versioned bucket | Same as the DB |
| Environment configuration and keys (`DJANGO_SECRET_KEY`, `PII_*`, DB passwords) | Secret store | On every change |

The DB and the file storage must be restorable to the same point in time (the metadata of photos, application documents, certificate PDFs and examination evidence lives in the DB table `media`). Redis is not backed up: it only holds the cache, locks and the queue, and sessions are also stored in the DB (`django_session`). The list of scheduled jobs (django-celery-beat) is in the DB too, and beat re-aligns it with `config/celery.py` when it starts.

`staticfiles/` and `static/dist/` are build output and are not backed up (`npm run build` and `collectstatic` recreate them).

## DB backup example

```bash
pg_dump -h db.internal -U app_migrator -d ninefruits -Fc -f ninefruits-$(date +%F).dump
```

`app_migrator` owns every schema (`public`, `audit`, `reporting`, `util`), so back up with this account. The roles (`app_*`) are cluster objects and are not part of the dump. On the restore server, create the roles first as described in [Installation](installation.md) section 2.

If you run `uv run manage.py audit_verify_chain` before the backup, the same command on the restored DB lets you compare the audit chains.

## Restore example

```bash
createdb -U postgres ninefruits_restore
psql -U postgres -d ninefruits_restore -v ON_ERROR_STOP=1 -f db/sql/roles/prepare_database.sql
pg_restore -U app_migrator -d ninefruits_restore --no-owner --role=app_migrator ninefruits-2026-10-22.dump
```

To run the application on the restored DB, set `DB_DATABASE=ninefruits_restore` and the **keys from the time of the backup** (`DJANGO_SECRET_KEY`, `PII_ENCRYPTION_KEY`, `PII_HASH_KEY`, and `PII_PREVIOUS_KEYS` if a key was rotated since). Then check the state:

```bash
DB_DATABASE=ninefruits_restore uv run manage.py migrate --check   # code and schema versions match
DB_DATABASE=ninefruits_restore uv run manage.py audit_verify_chain
```

If `migrate --check` reports migrations to apply, the backup is older than the current code. Restore with the code of the same version, or upgrade with `setup_install --force`.

## Restore drills

Every quarter, restore to a separate server and verify: signing in, decryption of personal data (**Show national ID number** on a person in the admin panel; keys match), viewing audit records and `audit_verify_chain`, opening files (photos, certificate PDFs), the certificate verification page. Record the outcome (time taken, problems).
