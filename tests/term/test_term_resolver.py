"""Original tests/Feature/Term/TermResolverTest.php: spring 2026 (grading), fall 2026 (in
session), spring 2027 (registration, staggered) at the same moment."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import StringIO
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command

from ninefruits.core.targeting import TargetCriteria
from ninefruits.term.enums import TermStatus, TermWindowType
from ninefruits.term.models import Term
from ninefruits.term.services import TermResolver
from tests.factories.term import TermFactory, TermTypeFactory, TermWindowFactory, academic_year_for

pytestmark = pytest.mark.django_db

SEOUL = ZoneInfo("Asia/Seoul")
AT = datetime(2026, 11, 10, 10, 0, tzinfo=SEOUL)


@dataclass
class Student:
    year_level: int

    def target_program_ids(self) -> list[int]:
        return []

    def target_org_unit_ids(self) -> list[int]:
        return []

    def target_admission_year(self) -> int | None:
        return 2024

    def target_year_level(self) -> int | None:
        return self.year_level

    def target_student_status(self) -> str | None:
        return "enrolled"

    def target_academic_standing(self) -> str | None:
        return None

    def target_tags(self) -> list[str]:
        return []


@pytest.fixture
def calendar() -> dict[str, Term]:
    spring = TermTypeFactory(code="spring")
    fall = TermTypeFactory(code="fall")
    y2026 = academic_year_for(2026)
    y2027 = academic_year_for(2027)

    def make(year: Any, term_type: Any, code: str, start: date, end: date, status: TermStatus) -> Term:
        term = TermFactory(academic_year=year, term_type=term_type, code=code, start_date=start, end_date=end)
        term.status = status
        term.save()
        return term

    terms = {
        "past": make(y2026, spring, "2026-SP", date(2026, 3, 2), date(2026, 6, 20), TermStatus.GRADES_CLOSED),
        "current": make(y2026, fall, "2026-FA", date(2026, 9, 1), date(2026, 12, 20), TermStatus.PUBLISHED),
        "next": make(y2027, spring, "2027-SP", date(2027, 3, 2), date(2027, 6, 20), TermStatus.PUBLISHED),
    }
    TermWindowFactory(
        term=terms["past"],
        window_type=TermWindowType.GRADE_APPEAL,
        opens_at=AT - timedelta(days=1),
        closes_at=AT + timedelta(days=1),
    )
    TermWindowFactory(
        term=terms["current"],
        window_type=TermWindowType.GRADE_ENTRY,
        opens_at=AT - timedelta(days=2),
        closes_at=AT + timedelta(days=5),
    )
    TermWindowFactory(
        term=terms["next"],
        window_type=TermWindowType.REGISTRATION,
        opens_at=AT - timedelta(hours=1),
        closes_at=AT + timedelta(days=3),
        eligibility=TargetCriteria(year_levels=[4]),
    )
    TermWindowFactory(
        term=terms["next"],
        window_type=TermWindowType.REGISTRATION,
        opens_at=AT + timedelta(days=1),
        closes_at=AT + timedelta(days=3),
        eligibility=TargetCriteria(year_levels=[1, 2, 3]),
    )
    return terms


def codes(terms: list[Term]) -> list[str]:
    return [term.code for term in terms]


def test_answers_each_business_question_with_its_own_term_at_the_same_time(calendar: dict[str, Term]) -> None:
    resolver = TermResolver()

    assert codes(resolver.in_session(AT)) == ["2026-FA"]
    assert codes(resolver.terms_open_for(TermWindowType.GRADE_ENTRY, at=AT)) == ["2026-FA"]
    assert codes(resolver.terms_open_for(TermWindowType.GRADE_APPEAL, at=AT)) == ["2026-SP"]
    assert codes(resolver.terms_open_for(TermWindowType.REGISTRATION, at=AT)) == ["2027-SP"]


def test_opens_registration_in_stages_by_eligibility(calendar: dict[str, Term]) -> None:
    resolver = TermResolver()

    assert codes(resolver.terms_open_for(TermWindowType.REGISTRATION, Student(4), AT)) == ["2027-SP"]
    assert resolver.terms_open_for(TermWindowType.REGISTRATION, Student(2), AT) == []
    next_window = resolver.next_window(TermWindowType.REGISTRATION, Student(2), AT)
    assert next_window is not None and next_window.opens_at == AT + timedelta(days=1)
    assert codes(resolver.terms_open_for(TermWindowType.REGISTRATION, Student(2), AT + timedelta(days=2))) == [
        "2027-SP"
    ]


def test_never_opens_windows_of_planned_or_archived_terms(calendar: dict[str, Term]) -> None:
    calendar["next"].status = TermStatus.PLANNED
    calendar["next"].save()

    assert TermResolver().open_windows(TermWindowType.REGISTRATION, AT) == []


def test_decides_the_term_in_session_by_the_institution_date(
    calendar: dict[str, Term], set_institution_settings: Callable[..., None]
) -> None:
    set_institution_settings(timezone="Asia/Seoul")

    # 2026-08-31 16:00 UTC is already 2026-09-01 in Seoul.
    moment = datetime(2026, 8, 31, 16, 0, tzinfo=ZoneInfo("UTC"))

    assert codes(TermResolver().in_session(moment)) == ["2026-FA"]


def test_shows_the_open_windows_with_term_inspect(
    calendar: dict[str, Term], set_institution_settings: Callable[..., None]
) -> None:
    set_institution_settings(timezone="Asia/Seoul")
    out = StringIO()

    assert call_command("term_inspect", at=AT.isoformat(), stdout=out) == 0

    output = out.getvalue()
    assert "In session" in output
    assert "2026-FA" in output
    assert "grade_entry" in output
    assert "2026-11-15 10:00 Asia/Seoul" in output
