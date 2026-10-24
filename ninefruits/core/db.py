"""PostgreSQL helpers: version-controlled SQL files and the session context read by row level
security policies and audit triggers (original App\\Support\\Database, ADR 0002)."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TypeVar

from django.conf import settings
from django.db import connections
from django.db.backends.signals import connection_created

T = TypeVar("T")

SQL_ROOT = Path(__file__).resolve().parent.parent.parent / "db"
_APPLY = re.compile(r"^-- @apply (\S+)\n", re.MULTILINE)


class SqlFile:
    """SQL files under db/. ``db/sql/`` holds the original functions, triggers, policies, views
    and role scripts verbatim; ``db/schema/`` holds the DDL each original migration executed,
    with ``-- @apply <path>`` markers where it applied a file from ``db/sql/``."""

    @staticmethod
    def path(relative: str) -> Path:
        path = (SQL_ROOT / relative.lstrip("/")).resolve()
        if SQL_ROOT not in path.parents or not path.is_file():
            raise FileNotFoundError(f"SQL file [{relative}] does not exist.")
        return path

    @classmethod
    def read(cls, relative: str) -> str:
        text = cls.path(relative).read_text(encoding="utf-8")
        parts = _APPLY.split(text)
        out: list[str] = []
        for index, part in enumerate(parts):
            if index % 2 == 1:
                out.append(cls.read(f"sql/{part}"))
            else:
                out.append(part)
        return cls._substitute_roles("".join(out))

    @staticmethod
    def _substitute_roles(sql: str) -> str:
        runtime = getattr(settings, "DB_RUNTIME_ROLE", "app_runtime")
        reporting = getattr(settings, "DB_REPORTING_ROLE", "app_reporting")
        if runtime != "app_runtime":
            sql = sql.replace('"app_runtime"', quote_identifier(runtime))
        if reporting != "app_reporting":
            sql = sql.replace('"app_reporting"', quote_identifier(reporting))
        return sql

    @classmethod
    def migration(cls, relative: str):  # type: ignore[no-untyped-def]
        """A ``RunSQL`` operation applying the file. Rollback is a no-op, like the original
        migrations that never drop audit history."""
        from django.db import migrations

        return migrations.RunSQL(cls.read(relative), reverse_sql=migrations.RunSQL.noop)


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


class DatabaseSessionContext:
    """Sets ``app.user_id``, ``app.actor``, ``app.request_id``, ``app.locale`` and
    ``app.fallback_locale`` on the runtime connection. Settings are session level, so they are
    reset when a request, task or command ends (connections are pooled and reused)."""

    KEYS = ("app.user_id", "app.actor", "app.request_id", "app.locale", "app.fallback_locale")

    def __init__(self, alias: str = "default") -> None:
        self.alias = alias
        self.baseline: dict[str, str] = {}
        self.state: dict[str, str] = {}
        self.stack: list[dict[str, str]] = []

    # -- public API ---------------------------------------------------------------------------
    def for_user(self, user_id: int | None, request_id: str | None = None) -> None:
        self.apply(
            {
                "app.user_id": "" if user_id is None else str(user_id),
                "app.actor": "" if user_id is None else f"user:{user_id}",
                "app.request_id": request_id or "",
            }
        )

    def for_system(self, name: str, initiated_by_user_id: int | None = None, request_id: str | None = None) -> None:
        """Celery tasks, scheduled tasks and commands. RLS policies grant system actors full access."""
        self.apply(
            {
                "app.user_id": "" if initiated_by_user_id is None else str(initiated_by_user_id),
                "app.actor": f"system:{name}",
                "app.request_id": request_id or "",
            }
        )

    def enter_system(self, name: str, initiated_by_user_id: int | None = None, request_id: str | None = None) -> None:
        self.stack.append(dict(self.state))
        self.for_system(name, initiated_by_user_id, request_id)

    def leave(self) -> None:
        if not self.stack:
            self.reset()
            return
        previous = self.stack.pop()
        self.apply({**dict.fromkeys(self.KEYS, ""), **previous})

    @contextmanager
    def system(self, name: str) -> Iterator[None]:
        """Runs a step as a system actor, keeping the initiating user in ``app.user_id`` so audit
        triggers still name them. The caller must have checked authorization first."""
        user_id = self.state.get("app.user_id") or None
        self.enter_system(name, int(user_id) if user_id else None, self.state.get("app.request_id") or None)
        try:
            yield
        finally:
            self.leave()

    def as_system(self, name: str, callback: Callable[[], T]) -> T:
        with self.system(name):
            return callback()

    def set_locale(self, locale: str, fallback_locale: str) -> None:
        self.apply({"app.locale": locale, "app.fallback_locale": fallback_locale})

    def reset(self) -> None:
        self.stack.clear()
        self.apply({**dict.fromkeys(self.KEYS, ""), **self.baseline})

    def use_baseline(self, values: dict[str, str]) -> None:
        """Values reset() returns to. Only tests use this (fixtures created as ``system:test``)."""
        self.baseline = dict(values)
        self.reset()

    def current(self) -> dict[str, str | None]:
        with connections[self.alias].cursor() as cursor:
            cursor.execute(
                "SELECT current_setting('app.user_id', true), current_setting('app.actor', true), "
                "current_setting('app.request_id', true), current_setting('app.locale', true), "
                "current_setting('app.fallback_locale', true)"
            )
            row = cursor.fetchone()
        return dict(zip(self.KEYS, row, strict=True))

    # -- internals ----------------------------------------------------------------------------
    def apply(self, values: dict[str, str]) -> None:
        self.state.update(values)
        connection = connections[self.alias]
        if connection.vendor != "postgresql":
            return
        if connection.connection is None and not any(values.values()):
            # Not connected and nothing to set: a fresh connection starts empty anyway.
            return
        placeholders = ", ".join(["set_config(%s, %s, false)"] * len(values))
        params: list[str] = []
        for key, value in values.items():
            params.extend((key, value))
        with connection.cursor() as cursor:
            cursor.execute("SELECT " + placeholders, params)  # placeholders only, values bound


_context = DatabaseSessionContext()


def session_context() -> DatabaseSessionContext:
    return _context


def _reapply_on_new_connection(sender, connection, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """A connection opened mid-request or mid-task (after a close) gets the current context."""
    if connection.alias != _context.alias:
        return
    values = {key: value for key, value in _context.state.items() if value}
    if values:
        placeholders = ", ".join(["set_config(%s, %s, false)"] * len(values))
        params: list[str] = []
        for key, value in values.items():
            params.extend((key, value))
        with connection.cursor() as cursor:
            cursor.execute("SELECT " + placeholders, params)


connection_created.connect(_reapply_on_new_connection, dispatch_uid="ninefruits.core.db.reapply")
