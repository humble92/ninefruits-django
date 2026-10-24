"""Shared fixtures for the security tests (original tests/Pest.php helpers)."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from django.core.cache import cache
from django.test import Client

from ninefruits.security.services.authorization import begin_scope
from ninefruits.settings.groups.authentication import AuthenticationSettings
from ninefruits.settings.groups.security import SecuritySettings


@pytest.fixture(autouse=True)
def _fresh_scope() -> Iterator[None]:
    cache.clear()
    begin_scope()
    yield
    begin_scope()
    cache.clear()


def _setter(group: type[Any]) -> Callable[..., None]:
    def set_values(**values: Any) -> None:
        settings = group.load()
        for name, value in values.items():
            setattr(settings, name, value)
        settings.save()

    return set_values


@pytest.fixture
def set_security_settings(db: None) -> Callable[..., None]:
    """Original ``setSecuritySettings``."""
    return _setter(SecuritySettings)


@pytest.fixture
def set_authentication_settings(db: None) -> Callable[..., None]:
    return _setter(AuthenticationSettings)


def confirm_password(client: Client) -> None:
    """A recent password confirmation (allauth reauthentication record)."""
    session = client.session
    session["account_authentication_methods"] = [{"method": "password", "at": time.time(), "reauthenticated": True}]
    session.save()


def signed_in(user: Any) -> Client:
    client = Client()
    client.force_login(user)
    return client


def create_org_unit(parent_id: int | None = None) -> int:
    """An org unit row (the OrgUnit model and factory arrive in Phase 1)."""
    import uuid

    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO org_unit_types (code, name, created_at, updated_at) VALUES (%s, %s, now(), now()) "
            "ON CONFLICT DO NOTHING",
            ["test_type", '{"en": "Test type"}'],
        )
        cursor.execute("SELECT id FROM org_unit_types WHERE code = %s", ["test_type"])
        type_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO org_units (code, name, org_unit_type_id, parent_id, effective_start_date, created_at, "
            "updated_at) "
            "VALUES (%s, %s, %s, %s, '2020-01-01', now(), now()) RETURNING id",
            [f"U{uuid.uuid4().hex[:8]}", '{"en": "Unit"}', type_id, parent_id],
        )
        return int(cursor.fetchone()[0])


def create_program(org_unit_id: int | None = None) -> int:
    import uuid

    from django.db import connection

    org_unit_id = org_unit_id or create_org_unit()
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO programs (code, name, degree_level, org_unit_id, effective_start_date, created_at, "
            "updated_at) "
            "VALUES (%s, %s, 'bachelor', %s, '2020-01-01', now(), now()) RETURNING id",
            [f"P{uuid.uuid4().hex[:8]}", '{"en": "Program"}', org_unit_id],
        )
        return int(cursor.fetchone()[0])
