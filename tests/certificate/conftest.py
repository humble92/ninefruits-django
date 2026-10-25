"""Fixtures for the certificate tests (original ``beforeEach`` of
``tests/Feature/Certificate/CertificateTest.php``): the essential data and the Korean
university certificate kinds, a certificate officer, a student record, and Gotenberg answered by
a fake (respx) unless a test is marked ``gotenberg``."""

from __future__ import annotations

import itertools
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import respx
from django.conf import settings
from django.test import Client

from ninefruits.certificate.actions import IssueCertificate
from ninefruits.certificate.models import CertificateType
from ninefruits.core.db import session_context
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.settings.groups.security import SecuritySettings
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory
from tests.reference_conftest import *  # noqa: F403

CONVERT = f"{settings.GOTENBERG_URL.rstrip('/')}/forms/chromium/convert/html"
_counter = itertools.count(1)


def fake_pdf(request: httpx.Request | None = None) -> httpx.Response:
    """A distinct small PDF per call (so a new rendering changes the checksum)."""
    return httpx.Response(200, content=b"%PDF-1.4\n% fake certificate " + str(next(_counter)).encode() + b"\n%%EOF\n")


@pytest.fixture(autouse=True)
def gotenberg(request: pytest.FixtureRequest) -> Iterator[Any]:
    if request.node.get_closest_marker("gotenberg"):
        yield None
        return
    with respx.mock(assert_all_called=False) as router:
        yield router.post(CONVERT).mock(side_effect=fake_pdf)


@pytest.fixture(autouse=True)
def _mfa_not_used(request: pytest.FixtureRequest) -> None:
    if "db" not in request.fixturenames and request.node.get_closest_marker("django_db") is None:
        return
    request.getfixturevalue("db")
    security = SecuritySettings.load()
    security.mfa_enforcement = MfaEnforcement.DISABLED
    security.save()


@pytest.fixture
def kinds(essential_data: None) -> dict[str, CertificateType]:
    """The profile's kinds (``seed_certificate_types``): ENR, GRD and TRN."""
    from ninefruits.setup.seeders.profiles.korean_university_certificates import seed_certificate_types

    seed_certificate_types()
    return {kind.code: kind for kind in CertificateType.objects.all()}


@pytest.fixture
def officer(kinds: dict[str, CertificateType]) -> Any:
    return UserFactory(
        permissions=[
            Permission.ADMIN_PANEL_ACCESS,
            Permission.CERTIFICATES_ISSUE,
            Permission.CERTIFICATES_MANAGE,
            Permission.STUDENT_RECORDS_VIEW,
        ]
    )


@pytest.fixture
def record(kinds: dict[str, CertificateType]) -> Any:
    return StudentRecordFactory()


@pytest.fixture
def issue_certificate() -> IssueCertificate:
    return IssueCertificate()


def signed_in(user: Any) -> Client:
    client = Client()
    client.force_login(user)
    session_context().reset()
    return client
