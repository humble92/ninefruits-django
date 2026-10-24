"""Lightweight domain event dispatcher (original Event/Listener). Events are dataclasses.
Synchronous listeners run immediately; queued listeners enqueue a Celery task after the
surrounding transaction commits (``afterCommit``)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from django.db import transaction

Listener = Callable[[Any], None]

_sync: dict[type, list[Listener]] = defaultdict(list)
_after_commit: dict[type, list[Listener]] = defaultdict(list)


def listen(event_type: type, *, after_commit: bool = False) -> Callable[[Listener], Listener]:
    def register(listener: Listener) -> Listener:
        registry = _after_commit if after_commit else _sync
        if listener not in registry[event_type]:
            registry[event_type].append(listener)
        return listener

    return register


def dispatch(event: Any) -> None:
    for listener in list(_sync[type(event)]):
        listener(event)
    for listener in list(_after_commit[type(event)]):
        transaction.on_commit(lambda listener=listener: listener(event))


def listeners_for(event_type: type) -> list[Listener]:
    return [*_sync[event_type], *_after_commit[event_type]]
