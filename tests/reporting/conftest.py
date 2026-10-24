"""Fixtures for the reporting tests: the shared reference fixtures (``essential_data``) and
two-factor authentication switched off for signed-in clients."""

from __future__ import annotations

import pytest

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
