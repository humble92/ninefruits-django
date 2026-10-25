"""Original tests/Feature/Term/TermSessionTest.php."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction

from ninefruits.term.actions import CopySessionWindows
from ninefruits.term.enums import TermWindowType
from ninefruits.term.models import Term
from ninefruits.term.services import TermResolver
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory, TermSessionFactory, TermWindowFactory

pytestmark = pytest.mark.django_db

UTC = ZoneInfo("UTC")


@pytest.fixture
def term() -> Term:
    return TermFactory(published=True, start_date=date(2026, 9, 1), end_date=date(2026, 12, 20))


def test_gives_every_term_a_full_term_session_that_follows_the_term_dates(term: Term) -> None:
    full = term.full_term_session()

    assert full.code == "FULL"
    assert {"en", "ko", "zh-hans"} <= set(full.name_translations)
    assert full.start_date == date(2026, 9, 1)

    term.end_date = date(2026, 12, 22)
    term.save()
    full.refresh_from_db()
    assert full.end_date == date(2026, 12, 22)


def test_keeps_sessions_inside_their_term(term: Term) -> None:
    with pytest.raises(DatabaseError, match="must lie within its term"), transaction.atomic():
        TermSessionFactory(term=term, start_date=date(2026, 8, 20), end_date=date(2026, 10, 1))

    TermSessionFactory(term=term, start_date=date(2026, 11, 1), end_date=date(2026, 11, 21), code="I")
    term.end_date = date(2026, 11, 15)
    with pytest.raises(ValidationError):
        term.save()


def test_puts_course_windows_on_a_session_and_term_windows_on_none(term: Term) -> None:
    drop_deadline = TermWindowFactory(term=term, window_type=TermWindowType.WITHDRAWAL)
    registration = TermWindowFactory(term=term, window_type=TermWindowType.REGISTRATION)

    assert drop_deadline.session_id == term.full_term_session().pk
    assert registration.session_id is None

    second = TermSessionFactory(term=term, start_date=date(2026, 10, 26), end_date=date(2026, 12, 20), code="B")
    with pytest.raises(DatabaseError, match="term_windows_session_check"), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("UPDATE term_windows SET term_session_id = %s WHERE id = %s", [second.pk, registration.pk])


def test_answers_per_session_whether_a_course_window_is_open(term: Term) -> None:
    at = datetime(2026, 11, 2, 10, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    second = TermSessionFactory(term=term, start_date=date(2026, 10, 26), end_date=date(2026, 12, 20), code="B")
    TermWindowFactory(
        term=term,
        window_type=TermWindowType.ADD_DROP,
        opens_at=at - timedelta(days=60),
        closes_at=at - timedelta(days=55),
    )
    TermWindowFactory(
        term=term,
        window_type=TermWindowType.ADD_DROP,
        opens_at=at - timedelta(days=1),
        closes_at=at + timedelta(days=1),
        session=second,
    )

    resolver = TermResolver()
    assert resolver.is_open_in_session(TermWindowType.ADD_DROP, second, at=at)
    assert not resolver.is_open_in_session(TermWindowType.ADD_DROP, term.full_term_session(), at=at)


def test_copies_the_full_term_windows_to_a_session_anchored_to_its_start_or_end(term: Term) -> None:
    full = term.full_term_session()
    TermWindowFactory(
        term=term,
        window_type=TermWindowType.ADD_DROP,
        opens_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        closes_at=datetime(2026, 9, 5, 18, 0, tzinfo=UTC),
    )
    TermWindowFactory(
        term=term,
        window_type=TermWindowType.GRADE_ENTRY,
        opens_at=datetime(2026, 12, 14, 9, 0, tzinfo=UTC),
        closes_at=datetime(2026, 12, 24, 18, 0, tzinfo=UTC),
    )
    second = TermSessionFactory(term=term, start_date=date(2026, 10, 26), end_date=date(2026, 12, 10), code="B")

    assert CopySessionWindows()(full, second, UserFactory()) == 2

    windows = {window.window_type: window for window in second.windows.all()}
    assert windows["add_drop"].opens_at.date() == date(2026, 10, 26)  # +55 days from the start
    assert windows["grade_entry"].closes_at.date() == date(2026, 12, 14)  # -10 days from the end


def test_stores_everyone_as_an_empty_object(term: Term) -> None:
    window = TermWindowFactory(term=term, eligibility=None)

    with connection.cursor() as cursor:
        cursor.execute("SELECT eligibility::text FROM term_windows WHERE id = %s", [window.pk])
        assert cursor.fetchone()[0] == "{}"
    window.refresh_from_db()
    assert window.eligibility.is_everyone()
