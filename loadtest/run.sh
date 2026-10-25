#!/usr/bin/env bash
# One load test run: gunicorn and a Celery worker against $DB_DATABASE, Locust headless, then
# the seat check (operations manual, load testing). Everything stops when the run ends.
#
#   DB_DATABASE=nf_load WORKERS=16 USERS=100 DURATION=1m loadtest/run.sh storage/loadtest/w16-u100
#
# Environment: WORKERS (gunicorn workers, default 4), USERS (default 100), SPAWN_RATE (default
# 20/s), DURATION (default 1m), TERM_ID (term for the seat check; default: the term with an open
# registration window), ADDRESSES (see registration.py), PORT (default 8000), and the usual
# Django variables (DB_DATABASE, DB_POOL, REDIS_URL, PRIVATE_MEDIA_ROOT, ...). The server runs
# behind one simulated proxy hop (TRUSTED_PROXY_COUNT=1) unless TRUSTED_PROXY_COUNT is set.
set -euo pipefail

out="${1:?usage: loadtest/run.sh <output prefix>}"
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
mkdir -p "$(dirname "$out")"

export UV_SYSTEM_CERTS=1
unset UV_NATIVE_TLS
export DJANGO_DEBUG="${DJANGO_DEBUG:-false}"
export TRUSTED_PROXY_COUNT="${TRUSTED_PROXY_COUNT:-1}"
export GUNICORN_WORKERS="${WORKERS:-4}"
port="${PORT:-8000}"
export GUNICORN_BIND="127.0.0.1:$port"

uv run gunicorn config.wsgi -c config/gunicorn.py >"$out.gunicorn.log" 2>&1 &
web=$!
uv run celery -A config worker --loglevel=WARNING --concurrency=2 >"$out.celery.log" 2>&1 &
worker=$!
trap 'kill $web $worker 2>/dev/null || true; wait 2>/dev/null || true' EXIT

for _ in $(seq 1 60); do
    curl -fsS -o /dev/null "http://127.0.0.1:$port/accounts/login/" 2>/dev/null && break
    sleep 1
done

status=0
uv run --group loadtest locust -f loadtest/registration.py --headless \
    -u "${USERS:-100}" -r "${SPAWN_RATE:-20}" -t "${DURATION:-1m}" \
    --host "http://127.0.0.1:$port" --csv "$out" --only-summary >"$out.locust.log" 2>&1 || status=$?

term="${TERM_ID:-$(PGPASSWORD="${DB_SUPERUSER_PASSWORD:-postgres}" psql -h "${DB_HOST:-127.0.0.1}" \
    -U "${DB_SUPERUSER_USERNAME:-postgres}" -d "${DB_DATABASE:?}" -Atc \
    "SELECT term_id FROM term_windows WHERE window_type = 'registration' AND now() BETWEEN opens_at AND closes_at LIMIT 1")}"
PGPASSWORD="${DB_SUPERUSER_PASSWORD:-postgres}" psql -h "${DB_HOST:-127.0.0.1}" \
    -U "${DB_SUPERUSER_USERNAME:-postgres}" -d "$DB_DATABASE" -v term="$term" \
    -f loadtest/seat_check.sql >"$out.seats.txt" 2>&1

tail -n 40 "$out.locust.log"
echo "seat check ($out.seats.txt):"
grep -c "(0 rows)" "$out.seats.txt" | sed 's/^/  queries with no rows: /'
exit "$status"
