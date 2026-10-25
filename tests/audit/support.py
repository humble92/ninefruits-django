"""Helpers shared by the audit, PII, media and command tests."""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from django.db import DatabaseError, connections, transaction

from ninefruits.security import authorization
from ninefruits.security.models.user import User

_sequence = itertools.count(1)


def make_user(email: str | None = None, **extra: Any) -> User:
    number = next(_sequence)
    extra.setdefault("name", f"Test User {number}")
    return User.objects.create_user(email or f"user{number}@example.test", "secret-password-123", **extra)


def database_error(callback: Any, using: str = "default") -> str | None:
    """Runs a query in a savepoint so an expected error does not abort the test transaction.
    Returns the error message, or None when it succeeded (original ``databaseError``)."""
    try:
        with transaction.atomic(using=using):
            callback()
    except DatabaseError as error:
        return str(error)
    return None


def scalar(sql: str, params: list[Any] | None = None, using: str = "default") -> Any:
    with connections[using].cursor() as cursor:
        cursor.execute(sql, params or [])
        row = cursor.fetchone()
    return None if row is None else row[0]


@contextmanager
def grants(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    """Grants catalog permissions to users for a test, independent of role assignments."""
    granted: dict[int, set[str]] = {}
    original = User.has_perm

    def has_perm(self: User, perm: str, obj: Any = None) -> bool:
        return self.is_active and (str(perm) in granted.get(self.pk, set()) or original(self, perm, obj))

    monkeypatch.setattr(User, "has_perm", has_perm)
    monkeypatch.setattr(User, "is_staff", property(lambda self: bool(granted.get(self.pk))))
    monkeypatch.setattr(authorization, "can_access_admin", lambda user: bool(granted.get(user.pk)))

    def grant(user: User, *permissions: str) -> User:
        granted.setdefault(user.pk, set()).update(str(permission) for permission in permissions)
        return user

    yield grant
