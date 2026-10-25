# Student information system manual (English)

For the staff who administer the system day to day and for the IT operators who install, deploy and maintain it. The screens are available in English (language menu).

Other languages: [한국어](../ko/README.md), [简体中文](../zh_Hans/README.md), [ລາວ](../lo/README.md). Korean is the source; the other editions are translations awaiting native review.

## Administrator manual

[admin/README.md](admin/README.md) — chapters 1 to 28, from getting started and users and roles through institution setup, admissions, registration, grades, certificates, graduation and LMS integration.

## Operations

| File | Contents |
|---|---|
| [installation.md](operations/installation.md) | Requirements, database roles, environment configuration, first installation and updates |
| [deployment-checklist.md](operations/deployment-checklist.md) | Python and gunicorn settings, production environment variables, deployment procedure, routine checks |
| [commands.md](operations/commands.md) | Reference for every management command (`uv run manage.py ...`): options, audit records, exit codes, examples |
| [scheduled-jobs.md](operations/scheduled-jobs.md) | Long-running processes (Celery worker, beat), scheduled jobs and queue jobs, how to detect failures (Flower) |
| [backup-restore.md](operations/backup-restore.md) | What to back up, dump and restore examples, restore drills |
| [security-keys.md](operations/security-keys.md) | The three secret keys, how to store them, personal data key rotation |
| [audit-and-maintenance.md](operations/audit-and-maintenance.md) | Audit hash chain, retention and pruning, file cleanup, health check |
| [load-testing.md](operations/load-testing.md) | Load test for the registration peak (Locust) and the worker count decision |
| [troubleshooting.md](operations/troubleshooting.md) | Common symptoms, what to check, per-request tracing |

## Other documents

- [LMS integration guide](../../lms-integration-guide.md): the API and LMS connectors (developers)
- [Adding a language](../../development/adding-a-language.md), [naming rules](../../development/naming.md), [review checklist](../../development/review-checklist.md) (developers)
- [Documentation index](../../README.md)
