"""Fixtures for the registration tests (original ``beforeEach`` blocks of
``tests/Feature/Registration``)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from ninefruits.offering.actions import SaveSectionMeeting
from ninefruits.registration.actions import EnrollStudent
from ninefruits.registration.data import EnrollOptions
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.settings.groups.security import SecuritySettings
from ninefruits.term.enums import TermWindowType
from tests.factories.facility import RoomFactory
from tests.factories.offering import SectionFactory
from tests.factories.organization import ProgramFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory, TermWindowFactory
from tests.reference_conftest import *  # noqa: F403

MEETING = {"weekday": 1, "start_time": "09:00", "end_time": "10:15"}


def now() -> Any:
    return timezone.now().replace(microsecond=0)


def upcoming_term(**kwargs: Any) -> Any:
    """Original ``Term::factory()->published()->between(now()->addMonth(), now()->addMonths(5))``."""
    today = timezone.localdate()
    return TermFactory(
        published=True, start_date=today + timedelta(days=31), end_date=today + timedelta(days=150), **kwargs
    )


def open_window(term: Any, window_type: TermWindowType, **kwargs: Any) -> Any:
    """A window from yesterday for a week (original ``between(now()->subDay(), now()->addWeek())``)."""
    return TermWindowFactory(
        term=term,
        window_type=window_type,
        opens_at=kwargs.pop("opens_at", now() - timedelta(days=1)),
        closes_at=kwargs.pop("closes_at", now() + timedelta(weeks=1)),
        **kwargs,
    )


def open_registration(term: Any) -> None:
    open_window(term, TermWindowType.REGISTRATION)
    open_window(term, TermWindowType.ADD_DROP)


@pytest.fixture(autouse=True)
def _mfa_not_used(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("concurrency") is not None:
        return  # no test transaction there
    request.getfixturevalue("db")
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


@pytest.fixture
def planner(db: None) -> Any:
    return UserFactory(permissions=[Permission.SECTIONS_MANAGE])


@pytest.fixture
def make_section(planner: Any) -> Callable[..., Any]:
    """Original ``registrationSection``: a published section with one meeting in a new room."""

    def make(term: Any, capacity: int = 30, meeting: dict[str, Any] | None = None, **attributes: Any) -> Any:
        section = SectionFactory(term=term, published=True, capacity=capacity, **attributes)
        SaveSectionMeeting()(section, {**(meeting or MEETING), "room_id": RoomFactory().pk}, planner)
        section.refresh_from_db()
        return section

    return make


@pytest.fixture
def make_student(db: None) -> Callable[..., tuple[Any, Any]]:
    """Original ``registrationStudent``: a record and its account."""

    def make(program: Any | None = None, **attributes: Any) -> tuple[Any, Any]:
        record = StudentRecordFactory(program=program or ProgramFactory(), **attributes)
        return record, UserFactory(person=record.person)

    return make


def enroll(record: Any, section: Any, actor: Any, options: EnrollOptions | None = None) -> Any:
    section.refresh_from_db()
    return EnrollStudent().handle(record, section, actor, options)
