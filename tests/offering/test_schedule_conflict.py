"""Original tests/Database/Offering/ScheduleConflictTest.php.

Phase 4 completion criterion: a room or an instructor cannot be booked twice at the same time,
enforced by the database (exclusion constraint, triggers) and explained by the application."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from ninefruits.offering.actions import AssignSectionInstructor, ChangeSectionStatus, SaveSectionMeeting
from ninefruits.offering.enums import InstructorRole, SectionStatus
from ninefruits.offering.models import Section
from ninefruits.security.enums import Permission
from tests.factories.facility import RoomFactory
from tests.factories.offering import SectionFactory
from tests.factories.person import InstructorFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory, TermSessionFactory

pytestmark = pytest.mark.django_db


def conflict_message(callback: Callable[[], Any]) -> str | None:
    try:
        callback()
    except ValidationError as error:
        return error.messages[0]
    return None


class Setup:
    def __init__(self) -> None:
        self.term = TermFactory(published=True, start_date=date(2026, 9, 1), end_date=date(2026, 12, 20))
        self.first_half = TermSessionFactory(
            term=self.term, start_date=date(2026, 9, 1), end_date=date(2026, 10, 25), code="A"
        )
        self.second_half = TermSessionFactory(
            term=self.term, start_date=date(2026, 10, 26), end_date=date(2026, 12, 20), code="B"
        )
        self.room = RoomFactory(capacity=50)
        self.instructor = InstructorFactory()
        self.staff = UserFactory(permissions=[Permission.SECTIONS_MANAGE])

    def section(self, session: Any = None) -> Section:
        return SectionFactory(term=self.term, session=session or self.term.full_term_session())

    def meet(self, section: Section, start: str, end: str, room: Any = None, weekday: int = 1) -> Any:
        return SaveSectionMeeting()(
            section,
            {"weekday": weekday, "start_time": start, "end_time": end, "room_id": (room or self.room).pk},
            self.staff,
        )

    def assign(self, section: Section) -> Any:
        return AssignSectionInstructor()(section, self.instructor, InstructorRole.PRIMARY, self.staff)


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_refuses_a_room_booked_at_an_overlapping_time_and_names_the_other_section(setup: Setup) -> None:
    first = setup.section()
    setup.meet(first, "09:00", "10:15")
    second = setup.section()

    message = conflict_message(lambda: setup.meet(second, "10:00", "11:15"))

    assert message is not None and first.label() in message
    assert conflict_message(lambda: setup.meet(second, "10:15", "11:30")) is None  # back to back is fine
    assert conflict_message(lambda: setup.meet(setup.section(), "09:30", "10:00", weekday=2)) is None  # other day


def test_lets_the_halves_of_a_term_share_a_room_at_the_same_time(setup: Setup) -> None:
    setup.meet(setup.section(setup.first_half), "09:00", "10:15")

    assert conflict_message(lambda: setup.meet(setup.section(setup.second_half), "09:00", "10:15")) is None
    assert conflict_message(lambda: setup.meet(setup.section(), "09:00", "10:15")) is not None


def test_refuses_an_instructor_at_two_places_whichever_is_assigned_first(setup: Setup) -> None:
    other_room = RoomFactory()
    first = setup.section()
    setup.meet(first, "13:00", "15:00")
    setup.assign(first)

    # Instructor first, then a meeting at the same time.
    second = setup.section()
    setup.assign(second)
    message = conflict_message(lambda: setup.meet(second, "14:00", "16:00", other_room))
    assert message is not None and first.label() in message

    # Meeting first, then the instructor.
    third = setup.section()
    setup.meet(third, "14:30", "15:30", RoomFactory())
    message = conflict_message(lambda: setup.assign(third))
    assert message is not None and first.label() in message


def test_frees_rooms_and_instructors_of_a_cancelled_section_and_checks_them_again_on_reopening(setup: Setup) -> None:
    first = setup.section()
    setup.meet(first, "09:00", "10:15")
    ChangeSectionStatus()(first, SectionStatus.CANCELLED, setup.staff, "Too few students")

    second = setup.section()
    setup.meet(second, "09:00", "10:15")

    first.refresh_from_db()
    message = conflict_message(lambda: ChangeSectionStatus()(first, SectionStatus.DRAFT, setup.staff))
    assert message is not None and second.label() in message


def test_enforces_the_rules_even_for_writes_that_bypass_the_application(setup: Setup) -> None:
    first = setup.section()
    setup.meet(first, "09:00", "10:15")
    second = setup.section()

    with pytest.raises(IntegrityError, match="section_meetings_room_excl"), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO section_meetings"
                " (section_id, weekday, start_time, end_time, room_id, start_date, end_date)"
                " VALUES (%s, 1, '09:30', '10:00', %s, '2026-09-01', '2026-12-20')",
                [second.pk, setup.room.pk],
            )
