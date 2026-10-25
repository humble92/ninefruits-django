"""Fixtures for the examination tests (original ``beforeEach`` of
``tests/Feature/Assessment/AssessmentTest.php``): essential data and the Korean university
profile (its four kinds), a staff member who records and manages, a student with an account, and
an English session in two weeks with two seats and the window open."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from ninefruits.assessment.actions import RecordAssessmentResult, RegisterForAssessment
from ninefruits.assessment.models import AssessmentSession, AssessmentType
from ninefruits.core.db import session_context
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.settings.groups.security import SecuritySettings
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory
from tests.reference_conftest import *  # noqa: F403

AREAS = ("LISTENING", "READING", "WRITING", "GRAMMAR")
STAFF_PERMISSIONS = [
    Permission.ADMIN_PANEL_ACCESS,
    Permission.ASSESSMENTS_RECORD,
    Permission.ASSESSMENTS_MANAGE,
    Permission.STUDENT_RECORDS_VIEW,
]


def scores(values: list[Any]) -> dict[str, Any]:
    """Original ``scores([...])``: listening, reading, writing, grammar."""
    return dict(zip(AREAS, values, strict=True))


def signed_in(user: Any) -> Client:
    client = Client()
    client.force_login(user)
    session_context().reset()
    return client


def student_of(record: Any) -> Any:
    return UserFactory(person=record.person)


@pytest.fixture(autouse=True)
def _mfa_not_used(request: pytest.FixtureRequest) -> None:
    if "db" not in request.fixturenames and request.node.get_closest_marker("django_db") is None:
        return
    request.getfixturevalue("db")
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


@pytest.fixture
def profile(essential_data: None) -> None:
    from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder

    KoreanUniversityProfileSeeder()()


@pytest.fixture
def world(profile: None, as_user: Any) -> dict[str, Any]:
    staff = UserFactory(permissions=STAFF_PERMISSIONS)
    record = StudentRecordFactory()
    now = timezone.now()
    english = AssessmentType.objects.get(code="ENG_COMP")
    session = AssessmentSession.objects.create(
        assessment_type=english,
        held_date=timezone.localdate() + timedelta(weeks=2),
        capacity=2,
        registration_opens_at=now - timedelta(days=1),
        registration_closes_at=now + timedelta(weeks=1),
    )
    return {
        "staff": staff,
        "record": record,
        "student": student_of(record),
        "english": english,
        "computer": AssessmentType.objects.get(code="COMP_EXAM"),
        "topik": AssessmentType.objects.get(code="TOPIK"),
        "session": session,
        "register": RegisterForAssessment(),
        "results": RecordAssessmentResult(),
        "as_user": as_user,
    }


def act(world: dict[str, Any], user: Any, call: Any) -> Any:
    """Runs an action with the user's database context (row level security applies)."""
    with world["as_user"](user):
        return call()


def set_minimum(kind: AssessmentType, code: str, value: Decimal | int | None) -> None:
    component = kind.components.get(code=code)
    component.min_score = None if value is None else Decimal(value)
    component.save(update_fields=["min_score", "updated_at"])
