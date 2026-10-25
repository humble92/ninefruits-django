"""Original tests/Database/Foundation/DatabaseSessionContextTest.php plus the connection reuse
cases of RowLevelSecurityTest (context reset after requests and tasks)."""

import pytest
from django.db import connections
from django.test import Client

from ninefruits.core.db import DatabaseSessionContext, session_context
from ninefruits.core.pool import reset_connection


def test_does_not_connect_for_an_empty_reset() -> None:
    connections["default"].close()
    context = DatabaseSessionContext()
    context.reset()
    assert connections["default"].connection is None


@pytest.mark.django_db
def test_sets_and_resets_the_user_context() -> None:
    context = session_context()
    context.for_user(42, "request-12345678")
    current = context.current()
    assert current["app.user_id"] == "42"
    assert current["app.actor"] == "user:42"
    assert current["app.request_id"] == "request-12345678"
    context.reset()
    assert context.current()["app.actor"] == "system:test"  # test baseline
    assert context.current()["app.user_id"] == ""


@pytest.mark.django_db
def test_system_context_keeps_the_initiating_user_and_restores() -> None:
    context = session_context()
    context.for_user(7)
    with context.system("matriculation"):
        current = context.current()
        assert current["app.actor"] == "system:matriculation"
        assert current["app.user_id"] == "7"
    assert context.current()["app.actor"] == "user:7"


@pytest.mark.django_db
def test_request_returns_to_the_baseline(client: Client) -> None:
    client.get("/accounts/login/")
    assert session_context().current()["app.actor"] == "system:test"


@pytest.mark.django_db
def test_pool_reset_clears_settings() -> None:
    raw = connections["default"]
    raw.ensure_connection()
    session_context().for_user(5)
    reset_connection(raw.connection)
    assert session_context().current()["app.user_id"] in ("", None)
    session_context().reset()
