"""Fixtures for the LMS tests (original ``beforeEach`` of ``tests/Feature/Lms/LmsTest.php``): MFA
off, the essential data and the 4.5 grade scale; a staff member with ``lms.manage``,
``sections.manage`` and ``registration.manage``; an active ``null`` platform ``TEST`` that pulls
scores; a term around today with a draft section (capacity 10) taught by an instructor with an
account; a student record with an account."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.lms.models import LmsPlatform
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import SectionInstructor
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.settings.groups.security import SecuritySettings
from tests.factories.offering import SectionFactory
from tests.factories.person import InstructorFactory, StudentRecordFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory
from tests.reference_conftest import *  # noqa: F403


@dataclass
class Lms:
    admin: Any
    platform: LmsPlatform
    term: Any
    section: Any
    teacher: Any
    record: Any
    student: Any


@pytest.fixture(autouse=True)
def _mfa_not_used(request: pytest.FixtureRequest) -> None:
    if "db" not in request.fixturenames and request.node.get_closest_marker("django_db") is None:
        return
    request.getfixturevalue("db")
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


@pytest.fixture
def lms(essential_data: None) -> Lms:
    from ninefruits.setup.seeders.profiles.korean_university import seed_scale_45

    seed_scale_45(True)
    admin = UserFactory(
        permissions=[
            Permission.ADMIN_PANEL_ACCESS,
            Permission.LMS_MANAGE,
            Permission.SECTIONS_MANAGE,
            Permission.REGISTRATION_MANAGE,
        ]
    )
    platform = LmsPlatform.objects.create(
        code="TEST",
        name={"en": "Test LMS", "ko": "테스트 LMS", "zh-hans": "测试 LMS"},
        driver="null",
        base_url="https://lms.test",
        options={},
        is_active=True,
        should_pull_grades=True,
    )
    today = timezone.localdate()
    term = TermFactory(published=True, start_date=today - timedelta(days=30), end_date=today + timedelta(days=90))
    section = SectionFactory(term=term, status=SectionStatus.DRAFT, capacity=10)
    instructor = InstructorFactory()
    SectionInstructor.objects.create(section=section, instructor=instructor, role="primary")
    teacher = UserFactory(person=instructor.person)
    record = StudentRecordFactory()
    student = UserFactory(person=record.person)
    return Lms(admin, platform, term, section, teacher, record, student)


def signed_in(user: Any) -> Client:
    client = Client()
    client.force_login(user)
    session_context().reset()
    return client
