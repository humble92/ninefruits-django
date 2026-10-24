"""Celery task base (porting-plan 9, 13.1). Every task runs as a system actor
(``system:task:<name>``) with the initiating request's id and user, and resets the database
session context when it ends. ``single_instance`` replaces ``ShouldBeUnique``/``onOneServer``."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from celery import Task, shared_task
from django.core.cache import cache

from ninefruits.core import context
from ninefruits.core.db import session_context

HEARTBEAT_CACHE_KEY = "system:heartbeat"


class SystemTask(Task):  # type: ignore[misc]
    abstract = True
    acks_late = True

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        headers = getattr(self.request, "headers", None) or {}
        request_id = headers.get("request_id") if isinstance(headers, dict) else None
        user_id = headers.get("user_id") if isinstance(headers, dict) else None
        db = session_context()
        db.enter_system(f"task:{self.name}", user_id, request_id)
        try:
            with context.bound(request_id=request_id, user_id=user_id, actor=f"system:task:{self.name}"):
                return super().__call__(*args, **kwargs)
        finally:
            db.leave()

    def apply_async(self, args: Any = None, kwargs: Any = None, **options: Any) -> Any:
        current = context.current()
        headers = {**current.as_headers(), **(options.pop("headers", None) or {})}
        return super().apply_async(args, kwargs, headers=headers, **options)


def single_instance(
    lock_name: str | None = None, timeout: int = 3600
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Skips the run when another worker holds the lock (Redis lock through the cache)."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = f"lock:{lock_name or func.__module__ + '.' + func.__name__}"
            if not cache.add(name, "1", timeout):
                return None
            try:
                return func(*args, **kwargs)
            finally:
                cache.delete(name)

        return wrapper

    return decorator


@shared_task(name="core.heartbeat", base=SystemTask)
@single_instance("core.heartbeat", timeout=55)
def heartbeat() -> None:
    """Every minute; ``system_health_check`` reports when it is stale."""
    from django.utils import timezone

    cache.set(HEARTBEAT_CACHE_KEY, timezone.now().isoformat(), 600)
