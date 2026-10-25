# Troubleshooting

- Audience: IT operators
- Related: [deployment checklist](deployment-checklist.md), [scheduled jobs](scheduled-jobs.md), [command reference](commands.md)

| Symptom | What to check |
|---|---|
| Redirected to the security page right after signing in | The two-factor policy is "required" and the grace period has passed. Resolved once the user enrolls. The policy is under **Settings > Security** |
| 403 in the admin panel | The user has no valid role assignment with the `admin_panel.access` permission (`Open the administration panel`). Open the user under **Users and access > Users** and check the **Role assignments** list (period, scope) |
| A menu item is missing | The role lacks the permission for that screen (for example `roles.view`) |
| Email codes do not arrive | Mail settings (`MAIL_*`, `DEFAULT_FROM_EMAIL`), the `Email code sent` entries under **Audit > Security events**, the sending limits (per user once a minute, five an hour) |
| The sign-in page answers `429 Too Many Requests` | One address exceeded `LOGIN_RATE_LIMIT_PER_IP` (default 30) attempts a minute. If many users are blocked at once, check that `TRUSTED_PROXY_COUNT` matches the real number of proxies (everyone appearing as the Nginx address); behind a campus NAT, raise the value ([deployment checklist](deployment-checklist.md#proxies-and-the-client-address)) |
| Sign-in fails with the right password | The sign-in is locked (`Sign-in locked` among the **security events**) or the account is inactive. Release a lock with `uv run manage.py security_unlock_user <email> --reason="..."` |
| A screen shows 0 rows of other people's data | May be normal (row level security). Confirm that the DB session actor is set by looking at the user column in **Audit > Data changes** |
| `400 Bad Request` | The requested host name is not in `DJANGO_ALLOWED_HOSTS` |
| `403 CSRF verification failed` | `DJANGO_CSRF_TRUSTED_ORIGINS` lacks the `https://` address, or Nginx does not pass `X-Forwarded-Proto` |
| Endless HTTPS redirects | Nginx does not pass `X-Forwarded-Proto $scheme`, so Django sees an HTTP request (`SECURE_PROXY_SSL_HEADER`) |
| Screens without styles or scripts, a `manifest.json` error | `npm ci && npm run build` (`static/dist/`), `collectstatic`, the Nginx `/static/` location. Production uses `VITE_DEV_MODE=false` |
| Parts of the screens appear in English | `compilemessages --ignore=.venv` was not run (no `.mo` files). For new strings, `uv run manage.py i18n_missing <locale>` |
| `permission denied for schema public` | The application attempted DDL as `app_runtime`. Run migrations only with `uv run manage.py migrate` or `setup_install` (both use `app_migrator` automatically) |
| `Audit records are append-only` | An attempt to update or delete an audit table. This block is intended |
| PDF generation fails | `uv run manage.py pdf_sample`, the Gotenberg status, `GOTENBERG_URL`, `GOTENBERG_TIMEOUT` |
| Queue tasks are stuck | Check the worker connection and failed tasks in Flower, `uv run celery -A config inspect active`, the Redis connection (`REDIS_URL`) |
| Scheduled jobs do not run, `/api/v1/health/` answers `degraded` | Beat has stopped (no scheduler heartbeat for more than 5 minutes). Check the beat process and its log. Only one beat |
| `Received unregistered task` in the worker log | The worker still runs the previous code. Restart the worker after deploying |
| A term close does not finish | Failed `grading.close_term_records` tasks in Flower. Fix the cause, then start the term close again (per-student calculations give the same result when run again) |

Per-request tracing: with the value of the `X-Request-Id` response header you can search the logs (`request_id` in the JSON), the activity log, the data changes and the security events together. When Nginx passes `X-Request-Id $request_id`, the Nginx access log joins in too. Command runs use a run ID starting with `cmd-`.
