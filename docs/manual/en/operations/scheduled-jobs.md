# Scheduled jobs and queues

- Audience: IT operators
- Related: [deployment checklist](deployment-checklist.md), [audit integrity](audit-and-maintenance.md), [command reference](commands.md)

## Long-running processes

| Process | Command | Check |
|---|---|---|
| Web | `uv run gunicorn config.wsgi -c config/gunicorn.py` | `GET /api/v1/health/` |
| Queue worker | `uv run celery -A config worker --loglevel=INFO` | **Workers** in Flower, `uv run celery -A config inspect ping` |
| Scheduler | `uv run celery -A config beat --loglevel=INFO` (**exactly one process overall**) | `scheduler` in `/api/v1/health/`, the beat log |
| Queue monitor (optional) | `uv run celery -A config flower --port=5555` | Only on the internal network or behind an Nginx access restriction |

All three use the same code and environment variables. A systemd example:

```ini
# /etc/systemd/system/ninefruits-celery.service
[Service]
User=ninefruits
WorkingDirectory=/srv/ninefruits
EnvironmentFile=/etc/ninefruits/env
ExecStart=/usr/local/bin/uv run --no-sync celery -A config worker --loglevel=INFO
KillSignal=SIGTERM
TimeoutStopSec=300
Restart=always
```

Create one more service of the same shape for beat with `ExecStart=... celery -A config beat --loglevel=INFO`. Even with several servers, enable the beat service on only one of them.

## Scheduled jobs

The registrations are the `beat_schedule` in `config/celery.py`; beat aligns the django-celery-beat database scheduler (`django_celery_beat_*` tables) with it when it starts. Times are in the server time zone (`APP_TIMEZONE`, UTC by default). Every scheduled job holds a Redis lock (`single_instance`), so the same job never runs twice at the same time.

| Job (Celery name) | Frequency | Command doing the same | Failure detection |
|---|---|---|---|
| `admission.expire_drafts` | Daily at 03:10 | `admission_expire_drafts` | Runs the command itself, so every run is recorded in the activity log (log `command`). If there is no record for more than a day, check beat and the worker |
| `registration.release_reserved_seats` | Every 5 minutes | `registration_release_reserved_seats` | No audit record. If seat allocations whose release time has passed still have an empty `release_processed_at`, check beat |
| `registration.promote_waitlists` | Hourly, on the hour | `waitlist_promote` | No activity log entry (promoted enrollments appear in the data changes as `system:task:registration.promote_waitlists`). The task result in Flower (sections, promotions) |
| `lms.reconcile` | Daily at 02:30 | `lms_reconcile` | Sync records per link (admin panel **LMS integration**), the task result in Flower |
| `audit.seal` | Daily at 03:30 | `audit_seal` | Seals the audit hash chain ([audit integrity](audit-and-maintenance.md)). Check if `audit_verify_chain` shows more unsealed rows than one day's worth |
| `core.heartbeat` | Every minute | None | Writes the last run time to the cache key `system:heartbeat`. `/api/v1/health/` answers `degraded` when it is more than 5 minutes old |

## Queue tasks

| Task (Celery name) | Triggered by | Notes |
|---|---|---|
| `pii.reencrypt_records` | `pii_reencrypt` | One task per batch of records (group). If a batch failed, run the command again (records already on the current key are skipped) |
| `registration.promote_waitlist` | Enrollment drop or withdrawal, seat allocation release | Only one runs per section (Redis lock, duplicates are prevented). Waitlist promotion re-checks every registration rule. Queued after the transaction commits |
| `grading.close_term_records`, `grading.finish_term_close` | `term_close`, closing a term in the admin panel | A chord: tasks of 100 students, then the finishing task (honors ranking, term status change, notifying the staff member who started it). Progress is the `job_batches` row `term-close:{term code}`, shown in the admin panel. A batch task retries up to 3 times on database errors; if it still fails, the whole batch is marked failed and the finishing task does not run. Fix the cause, then start the term close again (per-student calculations give the same result when run again) |
| `importing.import_chunk` | CSV import in the admin panel, `reference_import` | One task per chunk. Results in `imports`, failed rows in `failed_import_rows` (import results in the admin panel) |
| `lms.sync_section`, `lms.sync_enrollment` | Section and enrollment change events | On failure, retried up to 3 times a minute apart. The nightly `lms.reconcile` fixes what remains |

While a task runs, the DB actor is recorded as `system:task:{task name}` (for example `system:task:grading.close_term_records`), together with the request ID and the user of the request that queued it.

Flower shows failed tasks (**Tasks**, state `FAILURE`) and their exceptions. Celery tasks use `acks_late`, so a task interrupted by a dying worker runs again. Every task is built to give the same result when run again (idempotent).
