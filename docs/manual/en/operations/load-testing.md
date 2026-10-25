# Load testing (registration peak)

- Audience: IT operators
- Related: [deployment checklist](deployment-checklist.md), [installation](installation.md), [commands](commands.md)

Locust reproduces the first morning of registration, when many students rush to the same sections at once. The script is `loadtest/registration.py` (the original's k6 `tests/load/registration.js`), the run helper is `loadtest/run.sh`, and the over-enrollment check is `loadtest/seat_check.sql`.

[Manual contents](../README.md)

## Preparation

1. Create a database for load testing only (never the production database). Roles and the database are created as in section 2 of [installation](installation.md); then install and load the large demo. The student account list is written to `load-accounts.csv` in private storage (`PRIVATE_MEDIA_ROOT`, default `storage/private`).

   ```bash
   export DB_DATABASE=nf_load
   uv run manage.py setup_install --profile=korean-university --grade-scale=4.5 --force < /dev/null
   uv run manage.py setup_demo --size=large --seed=42 --student-accounts --force
   ```

2. A registration window must be open. The demo creates next term's registration windows by year (year 4 already open, year 3 in two days, years 1 and 2 in three days). To measure with every year, move the start of the other registration windows to the past under **Term windows** on the term's **Edit** page ([administrator manual, chapter 10](../admin/10-terms.md)), or run this as the superuser in the test database:

   ```sql
   UPDATE term_windows SET opens_at = now() - interval '1 hour'
    WHERE window_type = 'registration' AND opens_at > now() AND closes_at > now();
   ```

3. Redis and a Celery worker must run. Seats are decided in the database directly, but waitlist promotion, LMS synchronization and notifications go through the queue. If Redis is shared with other work, use another database number, e.g. `REDIS_URL=redis://127.0.0.1:6379/7`.

## Running

`loadtest/run.sh` starts gunicorn (`config/gunicorn.py`) and a Celery worker, runs Locust headless, runs the seat check and stops everything.

```bash
export DB_DATABASE=nf_load DB_POOL=true DB_POOL_MIN=1 DB_POOL_MAX=2 DB_PREPARE_THRESHOLD=2
WORKERS=9 USERS=100 DURATION=1m loadtest/run.sh storage/loadtest/w9-u100
```

To run it by hand, start the server with `TRUSTED_PROXY_COUNT=1` and run Locust:

```bash
TRUSTED_PROXY_COUNT=1 DJANGO_DEBUG=false GUNICORN_WORKERS=9 uv run gunicorn config.wsgi -c config/gunicorn.py
uv run --group loadtest locust -f loadtest/registration.py --headless -u 100 -r 20 -t 1m \
    --host http://127.0.0.1:8000 --csv storage/loadtest/run
psql -h 127.0.0.1 -U postgres -d nf_load -v term=<term id> -f loadtest/seat_check.sql
```

- Scenario: sign in (`/accounts/login/`) → registration page → course search (HTMX `?partial=results`) → register for the first section with open seats → drop it. Every iteration clears the cookies and signs in as the next student. Full sections and rule refusals are counted as normal outcomes (`registration outcomes`).
- The register and drop buttons post like HTMX (`HX-Request`); the server answers 302 to the registration page. The `enroll` and `drop` timings include that page (the browser needs it before it swaps `#registration`).
- Every student sends its own `X-Forwarded-For` address. With the server behind one proxy hop (`TRUSTED_PROXY_COUNT=1`), allauth's per-address sign-in limit applies per student address, as on a real campus. `ADDRESSES=1` reproduces every student behind one address (NAT).
- Environment: `ACCOUNTS` (account CSV), `SEARCH` (search text, default `GEN`), `ADDRESSES`, `FIRST_ACCOUNT` (first account, random by default). `run.sh` takes `WORKERS`, `USERS`, `SPAWN_RATE`, `DURATION`, `TERM_ID`, `PORT`.
- Raise `USERS` from 100 to 200 to 500 and watch the p95 of each page and the failure rate. Thresholds: registration page p95 < 800 ms, enroll p95 < 1.5 s, failures < 1 %. Locust exits with code 1 when a threshold fails.
- On the server, watch the connection count and lock waits in `pg_stat_activity` (`wait_event_type = 'Lock'`), the Celery backlog and CPU saturation. Locust on the same server uses CPU too, so the numbers are a lower bound.

## What the design guarantees

- Capacity is protected by the section row lock (`SeatAllocator.lock`, `SELECT ... FOR NO KEY UPDATE`) and CHECK constraints, so concurrent requests never over-enroll a section (`tests/registration/test_concurrent_registration.py`: 16 processes, 5 seats). The lock makes requests for seats of the same section wait for each other only; it does not block the foreign key checks of rows that merely reference the section (registration attempts, LMS sync logs).
- After a run, the four queries of `loadtest/seat_check.sql` must return no rows (over capacity, seat counter mismatch, seat group over capacity, duplicate enrollment in a section).
- The number of queries of the registration page does not grow with the registrations, waitlist entries or search results (`tests/registration/test_portal_query_count.py`).

## Sign-in limit per address and proxies

Besides the per-account failure limit (5 a minute), allauth applies a **per-address sign-in limit** (`LOGIN_RATE_LIMIT_PER_IP`, default `30/m/ip`), which the original did not have. The address the application sees is set by `TRUSTED_PROXY_COUNT` (`ninefruits.core.http.client_ip`).

- Behind Nginx with `TRUSTED_PROXY_COUNT=0` (the default), every request has the Nginx address. A campus that leaves through one NAT address is the same case.
- A run reproducing this (`ADDRESSES=1`, 100 VU, 1 minute): of 4,876 sign-ins **only 30 succeeded** and 4,846 were refused with 429 (49 % failures). Only 20 registrations went through in that minute. With one address per student under the same conditions, no sign-in was refused.
- Production settings: set `TRUSTED_PROXY_COUNT` to the number of proxies (`1` for one Nginx). If most students share one NAT address, raise `LOGIN_RATE_LIMIT_PER_IP` to the peak sign-in rate. Example: 2,000 students signing in within 10 minutes is 200 a minute from one address, so `300/m/ip`. An empty value removes the per-address limit (as in the original; the per-account failure limit remains).

## Server configuration decisions

- **gunicorn sync workers** (`config/gunicorn.py`). `GUNICORN_WORKERS` defaults to CPU cores × 2 + 1. Throughput was bound by the CPU: on 4 cores, 4, 9 and 16 workers gave the same throughput (23 to 26 requests a second). More workers only added database connections (12 → 36) and lock waits (peak 1 → 12). Do not go above cores × 2 + 1; scale out with more application servers.
- **Connection pool and prepared statements**: `DB_POOL=true`, `DB_POOL_MIN=1`, `DB_POOL_MAX=2`, `DB_PREPARE_THRESHOLD=2`. Because of the row level security (RLS) policies, query planning was most of a page's database time (31 queries of the registration page: 51 ms planning, 19 ms execution). Reusing connections and preparing statements with server-side binding plans each query once per connection. On the same 4 cores, throughput went from 16.8 to 25.6 requests a second, and the registration page median for one user from 160 ms to 97 ms. A server needs workers × `DB_POOL_MAX` + Celery concurrency connections, below PostgreSQL's `max_connections`. Behind PgBouncer in transaction mode prepared statements cannot be used: keep `DB_PREPARE_THRESHOLD=0`. The full test suite (1,066 tests) passes with these settings.
- **ASGI (the original's Octane decision)**: not adopted. Every page is a synchronous view, which ASGI would run in a thread without benefit, and throughput follows the CPU cores. Django does not bootstrap the application for every request (unlike PHP-FPM), so the gain Octane gives is already there; the gain of persistent connections comes from the pool and prepared statements above.
- Sign-in costs much CPU per request because of the Argon2 hash check (about 140 ms with one user). When sign-ins pile up at the peak, this cost eats into throughput first.

## Measurements of 2026-10-24

Environment: 4 vCPU (Xeon 2.1 GHz, `nproc` = 4), 15 GB RAM, a development machine shared with other work (test runs; load average 7 to 21 during the measurements), with Locust, gunicorn, PostgreSQL 18 and Redis on the same machine. Python 3.14, Django 6.1, gunicorn 26.2, `DJANGO_DEBUG=false`. Demo `--size=large --seed=42` (20,004 students, 11,437 student accounts, created in 416 seconds), the spring 2027 registration window open for every year, 52 published sections (2,262 seats). One minute each, `TRUSTED_PROXY_COUNT=1`, one address per student.

| Condition | Throughput | Page p95 | Enroll p95 | Failures | Registered / refused | Max PG connections |
|---|---|---|---|---|---|---|
| 2 VU, 9 workers, no pool | 5.1 req/s | 200 ms | 640 ms | 0 / 300 | 50 / 0 | 3 |
| 2 VU, 9 workers, pool + prepared statements | 6.2 req/s | 160 ms | 470 ms | 0 / 372 | 62 / 0 | 22 |
| 100 VU, 4 workers, no pool | 16.8 req/s | 6.0 s | 11 s | 0 / 1,005 | 52 / 86 | 6 |
| 100 VU, 16 workers, no pool | 17.1 req/s | 6.1 s | 11 s | 0 / 1,027 | 60 / 86 | 18 |
| 100 VU, 4 workers, pool + prepared statements | 25.6 req/s | 4.1 s | 7.0 s | 0 / 1,536 | 97 / 155 | 12 |
| 100 VU, 9 workers, pool + prepared statements | 25.4 req/s | 4.5 s | 7.3 s | 0 / 1,523 | 77 / 167 | 22 |
| 100 VU, 16 workers, pool + prepared statements | 23.4 req/s | 4.6 s | 8.4 s | 0 / 1,405 | 131 / 79 | 36 |
| 200 VU, 9 workers, pool + prepared statements | 29.8 req/s | 9.4 s | 14 s | 0 / 1,792 | 66 / 172 | 22 |
| 200 VU, 16 workers, pool + prepared statements | 29.2 req/s | 9.1 s | 14 s | 0 / 1,761 | 53 / 174 | 36 |
| 100 VU, 9 workers, one address (NAT) | (mostly 429) | 2.0 s | 3.3 s | 4,846 / 9,862 | 20 / 10 | 22 |

How to read it

- No HTTP failures in any run (except the one-address run) and no over-enrollment (`seat_check.sql` returned no rows). Refusals are full sections (`capacity`) and duplicate courses (`duplicate_course`, registrations left by iterations cut off at the end of an earlier run): normal behaviour.
- The delays of several seconds at 100 VU are the request queue. With one user, the server handles the page in about 100 ms and a registration (POST plus the returned page) in about 290 ms; this machine, sharing 4 cores between Locust, PostgreSQL and other work, tops out at 25 to 30 requests a second. On this machine the thresholds (page p95 < 800 ms, enroll p95 < 1.5 s) are not met at 100 VU.
- Lock waits came only from seat locks of the same section and were short (momentary peak of 1 to 12, more with more workers). Database connections stayed at or below workers × 2.
- Taking the registration peak as "2,000 students making 6 requests each within 10 minutes" gives 20 requests a second. This machine (pool + prepared statements) did 25 to 30, so a dedicated 8-core application server has headroom. Before going live: run the same script at 200 and 500 VU on a staging environment configured like production (dedicated application server, Nginx, separate database server, Locust on another machine) and confirm the thresholds.
- The original (Laravel, Sail development container, built-in server) did 24.7 req/s with 4 workers and 34.5 req/s with 16 at 100 VU. The machines differ, so the numbers do not compare directly.
