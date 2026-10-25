"""``system_health_check`` (original ``system:health-check``): settings, keys, database roles
and RLS, pending migrations, the permission catalog, Redis, the Celery workers, Gotenberg, the
private storage and the beat heartbeat. Exit code 2 when a check fails; ``--json`` for
monitoring."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.management.base import CommandParser
from django.db import connections
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from ninefruits.core.commands import StatusCommand

#: Tables whose row-level security must be on (original list).
RLS_TABLES = ("people", "student_records", "enrollments", "applications")
HEARTBEAT_STALE_AFTER = timedelta(minutes=5)
PROBE_FILE = ".health-check"

Probe = Callable[[], tuple[bool, str]]


def _secret_key() -> tuple[bool, str]:
    present = bool(settings.SECRET_KEY)
    return present, "DJANGO_SECRET_KEY " + ("set" if present else "missing")


def _pii_keys() -> tuple[bool, str]:
    present = bool(settings.PII_ENCRYPTION_KEY) and bool(settings.PII_HASH_KEY)
    return present, "PII_ENCRYPTION_KEY and PII_HASH_KEY " + ("set" if present else "missing")


def _debug_off() -> tuple[bool, str]:
    environment = str(settings.DJANGO_ENV)
    return (not settings.DEBUG or environment in ("local", "testing")), f"DEBUG={settings.DEBUG} ({environment})"


def _database() -> tuple[bool, str]:
    with connections["default"].cursor() as cursor:
        cursor.execute("SELECT current_user")
        runtime = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM pg_roles WHERE rolname = %s", ["app_reporting"])
        reporting = int(cursor.fetchone()[0])
    with connections["migrator"].cursor() as cursor:
        cursor.execute("SELECT current_user")
        migrator = cursor.fetchone()[0]
    ok = runtime != migrator and reporting > 0
    return ok, f"runtime {runtime}, migrator {migrator}, reporting role {'present' if reporting else 'missing'}"


def _row_level_security() -> tuple[bool, str]:
    with connections["default"].cursor() as cursor:
        cursor.execute(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace"
            " WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname = ANY(%s) AND NOT c.relrowsecurity"
            " ORDER BY c.relname",
            [list(RLS_TABLES)],
        )
        off = [row[0] for row in cursor.fetchall()]
    return not off, "enabled on the personal data tables" if not off else "disabled on: " + ", ".join(off)


def _migrations() -> tuple[bool, str]:
    executor = MigrationExecutor(connections["migrator"])
    pending = len(executor.migration_plan(executor.loader.graph.leaf_nodes()))
    return pending == 0, "up to date" if pending == 0 else f"{pending} pending"


def _permissions() -> tuple[bool, str]:
    from ninefruits.security.enums import Permission
    from ninefruits.security.models import Permission as PermissionRecord

    stored = set(PermissionRecord.objects.values_list("name", flat=True))
    missing = [str(permission) for permission in Permission if str(permission) not in stored]
    if not missing:
        return True, f"{len(Permission)} in sync"
    return False, "not synced: " + ", ".join(missing[:5]) + " (run security_sync_permissions)"


def _redis() -> tuple[bool, str]:
    uses_redis = "redis" in str(settings.CACHES["default"]["BACKEND"]).lower() or str(
        settings.CELERY_BROKER_URL
    ).startswith(("redis://", "rediss://"))
    if not uses_redis:
        return True, "not used"
    cache.set(PROBE_FILE, "1", 30)
    if cache.get(PROBE_FILE) != "1":
        return False, "cache does not answer"
    if str(settings.CELERY_BROKER_URL).startswith(("redis://", "rediss://")):
        import redis

        redis.Redis.from_url(str(settings.CELERY_BROKER_URL), socket_timeout=3).ping()
    return True, "ping ok"


def _queue() -> tuple[bool, str]:
    if settings.CELERY_TASK_ALWAYS_EAGER:
        return True, "tasks run eagerly (no workers)"
    from config.celery import app

    replies = app.control.inspect(timeout=2.0).ping() or {}
    if replies:
        return True, f"{len(replies)} Celery worker(s) answering"
    return False, "no Celery worker answers"


def _gotenberg() -> tuple[bool, str]:
    import httpx

    response = httpx.get(str(settings.GOTENBERG_URL).rstrip("/") + "/health", timeout=5)
    return response.is_success, f"HTTP {response.status_code}"


def _storage() -> tuple[bool, str]:
    storage = storages["default"]
    if storage.exists(PROBE_FILE):
        storage.delete(PROBE_FILE)
    name = storage.save(PROBE_FILE, ContentFile(timezone.now().isoformat().encode()))
    ok = storage.exists(name)
    storage.delete(name)
    return ok, "private storage " + ("writable" if ok else "not writable")


def _scheduler() -> tuple[bool, str]:
    from ninefruits.core.tasks import HEARTBEAT_CACHE_KEY

    value = cache.get(HEARTBEAT_CACHE_KEY)
    testing = settings.DJANGO_ENV == "testing"
    if not value:
        return testing, "no heartbeat yet (celery beat not running)"
    beat = datetime.fromisoformat(str(value))
    return (testing or timezone.now() - beat <= HEARTBEAT_STALE_AFTER), f"last run {value}"


CHECKS: tuple[tuple[str, Probe], ...] = (
    ("secret_key", _secret_key),
    ("pii_keys", _pii_keys),
    ("debug_off", _debug_off),
    ("database", _database),
    ("row_level_security", _row_level_security),
    ("migrations", _migrations),
    ("permissions", _permissions),
    ("redis", _redis),
    ("queue", _queue),
    ("gotenberg", _gotenberg),
    ("storage", _storage),
    ("scheduler", _scheduler),
)


class Command(StatusCommand):
    help = (
        "Check settings, keys, database roles and RLS, pending migrations, permissions, Redis, the Celery "
        "workers, Gotenberg, storage and the scheduler; exit 2 on a problem"
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--json", action="store_true", help="Machine-readable output")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        results = [self._run(name, probe) for name, probe in CHECKS]
        failed = sum(1 for result in results if not result["ok"])
        if options["json"]:
            self.stdout.write(json.dumps({"ok": failed == 0, "checks": results}, indent=4))
        else:
            for result in results:
                status = self.style.SUCCESS("OK  ") if result["ok"] else self.style.ERROR("FAIL")
                self.detail(f"{status} {result['check']}", str(result["detail"]))
            if failed == 0:
                self.info("All checks passed.")
            else:
                self.error(f"{failed} check(s) failed.")
        return self.SUCCESS if failed == 0 else self.PROBLEMS_FOUND

    @staticmethod
    def _run(name: str, probe: Probe) -> dict[str, Any]:
        try:
            ok, detail = probe()
        except Exception as error:  # every failure is a failed check, never a crash
            ok, detail = False, str(error)[:160]
        return {"check": name, "ok": bool(ok), "detail": detail}
