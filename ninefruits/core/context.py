"""Request context (request id, IP address, user agent, user) shared by logs, audit records and
Celery tasks. Laravel Context in the original; contextvars here so it also works in threads."""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    user_id: int | None = None
    actor: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def as_headers(self) -> dict[str, Any]:
        """Values passed to Celery tasks (see ninefruits.core.tasks)."""
        return {"request_id": self.request_id, "user_id": self.user_id, "ip_address": self.ip_address}


_current: contextvars.ContextVar[RequestContext] = contextvars.ContextVar(
    "ninefruits_request_context", default=RequestContext()
)


def current() -> RequestContext:
    return _current.get()


def update(**values: Any) -> RequestContext:
    context = replace(_current.get(), **values)
    _current.set(context)
    return context


def clear() -> None:
    _current.set(RequestContext())


@contextmanager
def bound(**values: Any) -> Iterator[RequestContext]:
    token = _current.set(replace(_current.get(), **values))
    try:
        yield _current.get()
    finally:
        _current.reset(token)
