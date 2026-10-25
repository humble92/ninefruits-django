"""Fixtures for the grading tests (original ``beforeEach`` blocks of ``tests/Feature/Grading``)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from django.utils import timezone

from ninefruits.grading.settings import GradingSettings
from ninefruits.offering.models import SectionInstructor
from ninefruits.security.enums import MfaEnforcement
from ninefruits.settings.groups.security import SecuritySettings
from ninefruits.term.enums import TermWindowType
from tests.factories.person import InstructorFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory, TermWindowFactory
from tests.reference_conftest import *  # noqa: F403

DEFAULTS: dict[str, Any] = {
    "gpa_decimals": 2,
    "gpa_rounding": "round",
    "retake_policy": "latest",
    "retake_max_grade": None,
    "relative_grade_caps": {"A": 30, "B": 40},
    "relative_cap_tolerance_percent": 1,
    "relative_minimum_students": 10,
    "standing_regular_terms_only": True,
    "warning_gpa_below": 1.75,
    "dismissal_warning_count": 0,
    "dismissal_consecutive_only": False,
    "honors_min_gpa": 4.0,
    "honors_min_credits": 15,
    "honors_exclude_failing": True,
}


def grading_settings(**values: Any) -> GradingSettings:
    """A settings object without the database (unit tests)."""
    return GradingSettings(**{**DEFAULTS, **values})


def set_grading(**values: Any) -> GradingSettings:
    settings = GradingSettings.load()
    for name, value in values.items():
        setattr(settings, name, value)
    settings.save()
    return settings


def now() -> Any:
    return timezone.now().replace(microsecond=0)


def running_term(**kwargs: Any) -> Any:
    """Original ``Term::factory()->published()->between(now()->subMonths(4), now()->addWeek())``."""
    today = timezone.localdate()
    return TermFactory(
        published=True, start_date=today - timedelta(days=120), end_date=today + timedelta(days=7), **kwargs
    )


def term_between(start: str | date, end: str | date, **kwargs: Any) -> Any:
    start = date.fromisoformat(start) if isinstance(start, str) else start
    end = date.fromisoformat(end) if isinstance(end, str) else end
    return TermFactory(published=True, start_date=start, end_date=end, **kwargs)


def open_grade_entry(term: Any) -> Any:
    """A grade entry window of the full-term session from yesterday for a week."""
    return TermWindowFactory(
        term=term,
        window_type=TermWindowType.GRADE_ENTRY,
        session=term.full_term_session(),
        opens_at=now() - timedelta(days=1),
        closes_at=now() + timedelta(weeks=1),
    )


def teacher_of(section: Any, instructor: Any = None) -> Any:
    """An instructor of the section with an account (original ``SectionInstructor::create``)."""
    instructor = instructor or InstructorFactory()
    SectionInstructor.objects.create(section=section, instructor=instructor, role="primary")
    user = getattr(instructor.person, "user", None)
    return user or UserFactory(person=instructor.person)


@pytest.fixture
def korean_scale(db: None) -> Any:
    """Original ``GradeScale::factory()->korean()->create()``: the 4.5 scale as the default."""
    from ninefruits.setup.seeders.profiles.korean_university import seed_scale_45

    return seed_scale_45(True)


@pytest.fixture(autouse=True)
def _mfa_not_used(request: pytest.FixtureRequest) -> None:
    if "db" not in request.fixturenames and request.node.get_closest_marker("django_db") is None:
        return
    request.getfixturevalue("db")
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()
