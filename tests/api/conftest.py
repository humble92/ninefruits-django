"""Fixtures for the API tests: MFA off, clean caches (throttle counters), API clients."""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from ninefruits.core.db import session_context
from ninefruits.security.enums import MfaEnforcement
from ninefruits.settings.groups.security import SecuritySettings
from tests.reference_conftest import *  # noqa: F403


@pytest.fixture(autouse=True)
def _mfa_not_used(request: pytest.FixtureRequest) -> None:
    if "db" not in request.fixturenames and request.node.get_closest_marker("django_db") is None:
        return
    request.getfixturevalue("db")
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


def session_client(user: Any) -> APIClient:
    """Signed in through the session, with CSRF checks like a browser."""
    client = APIClient(enforce_csrf_checks=False)
    client.force_login(user)
    session_context().reset()
    return client


def token_client(token: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    return client


def issue(user: Any, days: int | None = None) -> str:
    from ninefruits.api.actions import IssueApiToken

    return IssueApiToken()(user, user, days).token
