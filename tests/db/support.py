"""Helpers for database rule tests (original Pest helper ``databaseError``)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.db import DatabaseError, transaction


def database_error(callback: Callable[[], Any]) -> str | None:
    """Runs the callback in a savepoint and returns the database error message, or ``None``."""
    try:
        with transaction.atomic():
            callback()
    except DatabaseError as error:
        return str(error)
    return None
