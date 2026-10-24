"""Fixtures for the attendance tests (original ``beforeEach`` of
``tests/Feature/Attendance/AttendanceTest.php``): a term around today; a published section that
meets Mondays and Wednesdays 09:00-10:50 for eight weeks ending last week, with an instructor
account, three enrolled students (the first with an account) and a ``sections.manage`` staff
member."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.offering.models import SectionInstructor, SectionMeeting
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.settings.groups.security import SecuritySettings
from tests.factories.offering import SectionFactory
from tests.factories.person import InstructorFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory
from tests.reference_conftest import *  # noqa: F403


@dataclass
class Classroom:
    term: Any
    section: Any
    teacher: Any
    staff: Any
    enrollments: list[Any]
    student: Any


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


@pytest.fixture(autouse=True)
def _mfa_not_used(request: pytest.FixtureRequest) -> None:
    if "db" not in request.fixturenames and request.node.get_closest_marker("django_db") is None:
        return
    request.getfixturevalue("db")
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


@pytest.fixture
def classroom(essential_data: None) -> Classroom:
    today = timezone.localdate()
    term = TermFactory(published=True, start_date=today - timedelta(weeks=9), end_date=today + timedelta(weeks=6))
    section = SectionFactory(term=term, published=True)
    start = monday_of(today - timedelta(weeks=8))
    for weekday in (1, 3):
        SectionMeeting.objects.create(
            section=section,
            weekday=weekday,
            start_time=time(9, 0),
            end_time=time(10, 50),
            start_date=start,
            end_date=start + timedelta(weeks=8) - timedelta(days=1),
        )
    instructor = InstructorFactory()
    SectionInstructor.objects.create(section=section, instructor=instructor, role="primary")
    teacher = UserFactory(person=instructor.person)
    staff = UserFactory(
        permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.SECTIONS_MANAGE, Permission.SECTIONS_VIEW]
    )
    enrollments = EnrollmentFactory.create_batch(3, section=section)
    student = UserFactory(person=enrollments[0].student_record.person)
    return Classroom(term, section, teacher, staff, enrollments, student)


def signed_in(user: Any) -> Client:
    client = Client()
    client.force_login(user)
    session_context().reset()
    return client
