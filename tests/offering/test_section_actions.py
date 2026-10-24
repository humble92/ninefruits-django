"""Original tests/Feature/Offering/SectionActionsTest.php (+ the ``section_copy`` and
``schedule_check_conflicts`` commands)."""

from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command

from ninefruits.core import events
from ninefruits.offering.actions import (
    AssignSectionInstructor,
    ChangeSectionStatus,
    CopySections,
    CreateSection,
    SaveSectionMeeting,
    UpdateSection,
    UpdateSyllabus,
)
from ninefruits.offering.enums import InstructorRole, SectionStatus
from ninefruits.offering.events import SectionPublished
from ninefruits.offering.models import Section, SectionSeatGroup
from ninefruits.security.enums import Permission, ScopeType
from tests.factories.curriculum import CourseFactory, CourseVersionFactory
from tests.factories.facility import RoomFactory
from tests.factories.offering import SectionFactory
from tests.factories.organization import OrgUnitFactory
from tests.factories.person import InstructorFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory, TermSessionFactory

pytestmark = pytest.mark.django_db


class Setup:
    def __init__(self) -> None:
        self.fall = TermFactory(
            published=True, start_date=date(2026, 9, 1), end_date=date(2026, 12, 20), code="2026-FA"
        )
        self.spring = TermFactory(
            published=True, start_date=date(2027, 3, 2), end_date=date(2027, 6, 20), code="2027-SP"
        )
        self.course = CourseFactory(
            version={"effective_start_date": date(2020, 3, 1), "effective_end_date": date(2027, 2, 28), "credits": 3}
        )
        CourseVersionFactory(course=self.course, effective_start_date=date(2027, 3, 1), credits=4)
        self.planner = UserFactory(permissions=[Permission.SECTIONS_MANAGE], email="planner@example.test")
        self.room = RoomFactory(capacity=60)
        self.instructor = InstructorFactory()

    def fall_section(self, **meeting: Any) -> Section:
        section = CreateSection()(
            self.fall.full_term_session(), self.course, {"section_code": "01", "capacity": 40}, self.planner
        )
        AssignSectionInstructor()(section, self.instructor, InstructorRole.PRIMARY, self.planner)
        SaveSectionMeeting()(
            section,
            {"weekday": 1, "start_time": "09:00", "end_time": "10:15", "room_id": self.room.pk, **meeting},
            self.planner,
        )
        section.refresh_from_db()
        return section


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_offers_the_course_version_in_effect_when_the_session_starts_within_the_planners_scope(setup: Setup) -> None:
    fall_section = setup.fall_section()
    spring_section = CreateSection()(
        setup.spring.full_term_session(), setup.course, {"section_code": "01", "capacity": 40}, setup.planner
    )

    assert fall_section.version.credits == Decimal("3.0")
    assert spring_section.version.credits == Decimal("4.0")

    other_unit = UserFactory(
        permissions=[Permission.SECTIONS_MANAGE],
        permissions__scope_type=ScopeType.ORG_UNIT,
        permissions__scope_id=OrgUnitFactory().pk,
    )
    with pytest.raises(PermissionDenied):
        CreateSection()(
            setup.spring.full_term_session(), setup.course, {"section_code": "02", "capacity": 40}, other_unit
        )


def test_refuses_a_section_number_used_twice(setup: Setup) -> None:
    setup.fall_section()
    with pytest.raises(ValidationError) as error:
        CreateSection()(
            setup.fall.full_term_session(), setup.course, {"section_code": "01", "capacity": 40}, setup.planner
        )
    assert "section_code" in error.value.message_dict


def test_moves_meetings_with_the_section_to_another_session(setup: Setup) -> None:
    section = setup.fall_section()
    second = TermSessionFactory(term=setup.fall, start_date=date(2026, 10, 26), end_date=date(2026, 12, 20), code="B")

    UpdateSection()(section, {"term_session_id": second.pk}, setup.planner)

    assert section.meetings.first().start_date == date(2026, 10, 26)


def test_copies_a_term_into_the_next_as_drafts_reporting_what_it_could_not_keep(setup: Setup) -> None:
    section = setup.fall_section()
    SectionSeatGroup.objects.create(
        section=section,
        name={"en": "Majors"},
        capacity=20,
        releases_at=datetime(2026, 8, 28, 9, 0, tzinfo=ZoneInfo("UTC")),
    )
    UpdateSyllabus()(section, "en", {"overview": "Lists and trees"}, setup.planner, publish=True)

    # In spring the room is taken at that time by another course.
    other = SectionFactory(term=setup.spring)
    SaveSectionMeeting()(
        other, {"weekday": 1, "start_time": "09:00", "end_time": "10:15", "room_id": setup.room.pk}, setup.planner
    )

    preview = CopySections()(setup.fall, setup.spring, setup.planner, dry_run=True)
    assert preview.created == [section.label()]
    assert Section.objects.filter(term=setup.spring).count() == 1

    report = CopySections()(setup.fall, setup.spring, setup.planner)
    copy = Section.objects.get(term=setup.spring, course=setup.course)

    assert copy.status == SectionStatus.DRAFT
    assert copy.version.credits == Decimal("4.0")
    assert list(copy.instructors.values_list("pk", flat=True)) == [setup.instructor.pk]
    assert copy.meetings.first().room_id is None
    assert len(report.notes[section.label()]) == 1
    # shifted by the 182 days between the term starts
    assert copy.seat_groups.first().releases_at.date() == date(2027, 2, 26)
    assert copy.syllabus.published_at is None
    assert copy.copied_from_section_id == section.pk

    assert section.label() in CopySections()(setup.fall, setup.spring, setup.planner).skipped


def test_lets_the_sections_instructors_and_planners_write_the_syllabus_nobody_else(setup: Setup) -> None:
    section = setup.fall_section()
    teacher = UserFactory(person=setup.instructor.person)

    UpdateSyllabus()(
        section, "ko", {"overview": "개요", "weekly_plan": [{"week": 1, "topic": "소개"}]}, teacher, publish=True
    )

    section.refresh_from_db()
    assert section.syllabus.published_at is not None
    with pytest.raises(PermissionDenied):
        UpdateSyllabus()(section, "ko", {}, UserFactory())
    with pytest.raises(ValidationError):
        UpdateSyllabus()(section, "ko", {"weekly_plan": [{"week": 99, "topic": "x"}]}, teacher)


def test_publishing_dispatches_section_published_and_cancelling_needs_a_reason(setup: Setup) -> None:
    section = setup.fall_section()
    received: list[Any] = []
    listener = events.listen(SectionPublished)(received.append)
    try:
        ChangeSectionStatus()(section, SectionStatus.PUBLISHED, setup.planner)
    finally:
        events._sync[SectionPublished].remove(listener)
    assert [event.section.pk for event in received] == [section.pk]
    with pytest.raises(ValidationError):
        ChangeSectionStatus()(section, SectionStatus.CANCELLED, setup.planner)


def test_copies_and_checks_terms_from_the_command_line(setup: Setup) -> None:
    setup.fall_section()
    type(setup.room).objects.filter(pk=setup.room.pk).update(capacity=20)

    out = io.StringIO()
    status = call_command("schedule_check_conflicts", "2026-FA", stdout=out, stderr=io.StringIO())
    assert status == 2
    assert "holds 20" in out.getvalue()

    assert call_command("section_copy", "2026-FA", "2027-SP", stdout=io.StringIO(), stderr=io.StringIO()) == 1
    out = io.StringIO()
    status = call_command(
        "section_copy",
        "2026-FA",
        "2027-SP",
        actor="planner@example.test",
        dry_run=True,
        stdout=out,
        stderr=io.StringIO(),
    )
    assert status == 0
    assert "Dry run: 1 section(s) copied" in out.getvalue()
    assert not Section.objects.filter(term=setup.spring).exists()

    status = call_command(
        "section_copy", "2026-FA", "2027-SP", actor="planner@example.test", stdout=io.StringIO(), stderr=io.StringIO()
    )
    assert status == 0
    assert Section.objects.filter(term=setup.spring).count() == 1
