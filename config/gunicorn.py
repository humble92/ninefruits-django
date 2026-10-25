"""gunicorn settings: ``uv run gunicorn config.wsgi -c config/gunicorn.py``.

Sync workers (one request at a time per process; the application is plain WSGI with blocking
database calls). Everything comes from environment variables so one file serves every server;
the measurements behind the defaults are in the operations manual, load testing chapter.

- ``GUNICORN_BIND``: address or ``unix:/run/ninefruits/gunicorn.sock`` (default ``127.0.0.1:8000``;
  never expose gunicorn directly, put Nginx in front).
- ``GUNICORN_WORKERS``: worker processes (default: 2 per CPU core + 1). Throughput grows with
  the worker count until the CPUs are busy; the database is not the limit.
- ``GUNICORN_TIMEOUT``: seconds before a stuck worker is restarted (default 60; long exports run
  in Celery, not in a request).
- ``GUNICORN_MAX_REQUESTS``: restart a worker after this many requests (default 2000, with jitter)
  so slow memory growth never accumulates.
- ``GUNICORN_FORWARDED_ALLOW_IPS``: proxies whose ``X-Forwarded-Proto`` gunicorn trusts (default
  ``127.0.0.1``). The client address for rate limits and audit is ``TRUSTED_PROXY_COUNT`` in the
  Django settings (``ninefruits.core.http.client_ip``), not this setting.

Database connections: with ``DB_POOL=true`` each worker keeps its own psycopg pool, so a server
needs about ``GUNICORN_WORKERS x DB_POOL_MAX`` connections (plus Celery). A sync worker uses one
connection at a time: ``DB_POOL_MIN=1``, ``DB_POOL_MAX=2`` is enough.
"""

from __future__ import annotations

import multiprocessing
import os


def _int(name: str, default: int) -> int:
    value = os.environ.get(name, "").strip()
    return int(value) if value else default


bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = _int("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1)
worker_class = "sync"
timeout = _int("GUNICORN_TIMEOUT", 60)
graceful_timeout = _int("GUNICORN_GRACEFUL_TIMEOUT", 30)
keepalive = _int("GUNICORN_KEEPALIVE", 5)
max_requests = _int("GUNICORN_MAX_REQUESTS", 2000)
max_requests_jitter = max_requests // 10
# Connections are opened lazily per worker after the fork; preloading saves memory only.
preload_app = False
forwarded_allow_ips = os.environ.get("GUNICORN_FORWARDED_ALLOW_IPS", "127.0.0.1")
# Nginx keeps the access log; set GUNICORN_ACCESS_LOG=- to log requests here as well.
accesslog = os.environ.get("GUNICORN_ACCESS_LOG") or None
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
