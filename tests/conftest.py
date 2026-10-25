"""Test database: created by the superuser, migrated as app_migrator, used as app_runtime so row
level security applies (porting-plan 5.3, 7.4). Fixtures are created as the system actor
``system:test``; requests run as the signed-in user and return to that baseline."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connections

from ninefruits.core import provision
from ninefruits.core.db import session_context

DB_FIXTURES = ("db", "transactional_db", "django_db_reset_sequences", "django_db_serialized_rollback")


def pytest_configure(config: pytest.Config) -> None:
    # Compiled gettext catalogs (.mo) are not in git: compile the stale ones once per run.
    from ninefruits.i18n.pytest_plugin import pytest_configure as compile_catalogs

    compile_catalogs(config)


def _test_database_name() -> str:
    name = settings.DATABASES["default"]["TEST"]["NAME"]
    worker = os.environ.get("PYTEST_XDIST_WORKER")
    return f"{name}_{worker}" if worker else name


def _use_database(name: str) -> None:
    for alias in ("default", "migrator"):
        settings.DATABASES[alias]["NAME"] = name
        connections[alias].close()
        connections[alias].settings_dict["NAME"] = name


@pytest.fixture(scope="session")
def django_db_setup(request: pytest.FixtureRequest, django_db_blocker: Any) -> Iterator[None]:
    name = _test_database_name()
    reuse = request.config.getoption("reuse_db", False) and not request.config.getoption("create_db", False)
    with django_db_blocker.unblock():
        with provision.superuser_connect() as conn:
            if not (reuse and provision.database_exists(conn, name)):
                provision.drop_database(conn, name)
                provision.create_database(conn, name)
                created = True
            else:
                created = False
        if created:
            provision.prepare_database(name)
        _use_database(name)
        call_command("migrate", database="migrator", verbosity=0, interactive=False)
        connections["migrator"].close()
    yield
    if not reuse:
        with django_db_blocker.unblock():
            for alias in ("default", "migrator"):
                connections[alias].close()
            with provision.superuser_connect() as conn:
                provision.drop_database(conn, name)


@pytest.fixture(autouse=True)
def _system_test_actor(request: pytest.FixtureRequest) -> Iterator[None]:
    uses_db = request.node.get_closest_marker("django_db") is not None or any(
        fixture in request.fixturenames for fixture in DB_FIXTURES
    )
    if not uses_db:
        yield
        return
    request.getfixturevalue("_django_db_helper")
    context = session_context()
    context.use_baseline({"app.actor": "system:test"})
    yield
    context.baseline = {}
    context.state = {}
    context.stack.clear()


@pytest.fixture(autouse=True)
def _clear_request_context() -> Iterator[None]:
    """Login listeners bind the user to the request context; never leak it into the next test."""
    from ninefruits.core import context as request_context

    request_context.clear()
    yield
    request_context.clear()


@pytest.fixture
def without_baseline() -> Iterator[None]:
    """For tests of the database policies themselves: no system actor."""
    context = session_context()
    context.use_baseline({})
    yield


@pytest.fixture
def as_user() -> Any:
    """``with as_user(user): ...`` runs direct Action calls with the user's database context,
    like a real request (original Livewire database context hook)."""

    @contextmanager
    def _as_user(user: Any) -> Iterator[Any]:
        context = session_context()
        context.for_user(user.pk)
        try:
            yield user
        finally:
            context.reset()

    return _as_user
