from __future__ import annotations

from django.db import IntegrityError

UNIQUE_VIOLATION = "23505"


def is_unique_violation(error: IntegrityError) -> bool:
    cause = error.__cause__ or error
    return getattr(cause, "sqlstate", None) == UNIQUE_VIOLATION
