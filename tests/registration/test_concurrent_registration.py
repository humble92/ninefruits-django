"""Phase 5 completion criterion (original ``tests/Database/Registration/ConcurrentRegistrationTest.php``):
concurrent requests never exceed the capacity. Sixteen real processes, each with its own database
connection, register different students into one five-seat section at the same moment.

The fixtures are committed (no test transaction: the other processes could not see it) and
removed afterwards. Run separately: ``uv run pytest -m concurrency``."""

from __future__ import annotations

import multiprocessing
import time
from collections import Counter
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.db import connections
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.term.enums import TermWindowType

from .workers import enroll_once

pytestmark = pytest.mark.concurrency

CAPACITY = 5
STUDENTS = 16


def _models() -> list[Any]:
    """Tables the fixtures write, children first (for the clean-up)."""
    from ninefruits.curriculum.models import Course, CourseVersion
    from ninefruits.offering.models import Section, SectionInstructor, SectionMeeting, SectionSeatGroup
    from ninefruits.organization.models import OrgUnit, OrgUnitType, Program
    from ninefruits.person.models import Person, StudentRecord
    from ninefruits.registration.models import Enrollment, RegistrationAttempt, WaitlistEntry
    from ninefruits.term.models import AcademicYear, Term, TermSession, TermType, TermWindow

    return [
        RegistrationAttempt,
        WaitlistEntry,
        Enrollment,
        SectionMeeting,
        SectionInstructor,
        SectionSeatGroup,
        Section,
        TermWindow,
        TermSession,
        Term,
        AcademicYear,
        TermType,
        CourseVersion,
        Course,
        StudentRecord,
        Person,
        Program,
        OrgUnit,
        OrgUnitType,
    ]


@pytest.fixture
def committed(django_db_setup: None, django_db_blocker: Any) -> Iterator[None]:
    """Database access without a test transaction; rows created during the test are deleted by
    the schema owner afterwards."""
    with django_db_blocker.unblock():
        migrator = "migrator"
        before = {
            model: (model._base_manager.using(migrator).order_by("-pk").values_list("pk", flat=True).first() or 0)
            for model in _models()
        }
        context = session_context()
        context.for_system("test:concurrency")
        try:
            yield
        finally:
            context.reset()
            for model, last in before.items():
                model._base_manager.using(migrator).filter(pk__gt=last)._raw_delete(migrator)
            for alias in ("default", "migrator"):
                connections[alias].close()


def test_never_seats_more_students_than_the_capacity_under_concurrent_requests(committed: None) -> None:
    from ninefruits.offering.models import Section
    from ninefruits.registration.models import Enrollment
    from tests.factories.offering import SectionFactory
    from tests.factories.person import StudentRecordFactory
    from tests.factories.term import TermFactory, TermWindowFactory

    today = timezone.localdate()
    term = TermFactory(published=True, start_date=today + timedelta(days=31), end_date=today + timedelta(days=150))
    now = timezone.now().replace(microsecond=0)
    TermWindowFactory(
        term=term,
        window_type=TermWindowType.REGISTRATION,
        opens_at=now - timedelta(hours=1),
        closes_at=now + timedelta(hours=1),
    )
    section = SectionFactory(term=term, published=True, capacity=CAPACITY)
    record_ids = [StudentRecordFactory().pk for _ in range(STUDENTS)]
    database = connections["default"].settings_dict["NAME"]

    spawn = multiprocessing.get_context("spawn")
    results = spawn.Queue()
    start_at = time.time() + 8.0  # every child is set up and waiting by then
    children = [
        spawn.Process(target=enroll_once, args=(database, record_id, section.pk, start_at, results))
        for record_id in record_ids
    ]
    for child in children:
        child.start()
    outcomes = [results.get(timeout=120) for _ in children]
    for child in children:
        child.join(timeout=60)

    counts = Counter(outcome for _record, outcome in outcomes)
    assert counts == {"enrolled": CAPACITY, "full": STUDENTS - CAPACITY}, counts
    assert Section.objects.get(pk=section.pk).enrolled_count == CAPACITY
    assert Enrollment.objects.filter(section=section, status="enrolled").count() == CAPACITY
