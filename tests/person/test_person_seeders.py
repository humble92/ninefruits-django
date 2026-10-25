"""Essential and demo seeders of the person app (original ``StatusChangeTypeSeeder`` and
``DemoPeopleSeeder``; idempotency as in tests/Feature/Setup/SetupCommandsTest.php)."""

from __future__ import annotations

from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import AdvisorAssignment, Instructor, StudentRecord, StudentStatusChangeType
from ninefruits.security.enums import Persona
from ninefruits.security.models import User
from ninefruits.security.services.personas import PersonaResolver, registered_detectors
from ninefruits.setup.seeders.demo.options import DemoOptions, use_options
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder, _Names
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from ninefruits.setup.seeders.essential.status_change_type import StatusChangeTypeSeeder

pytestmark = pytest.mark.django_db


def test_seeds_the_system_status_change_types_idempotently_and_keeps_edits() -> None:
    StatusChangeTypeSeeder()()
    leave = StudentStatusChangeType.objects.get(code="leave_of_absence")
    assert StudentStatusChangeType.objects.filter(is_system=True).count() == 6
    assert leave.name_translations["ko"] == "휴학"
    assert leave.from_statuses == ["enrolled"]

    leave.name = {"en": "Leave"}
    leave.can_student_request = False
    leave.to_status = StudentStatus.WITHDRAWN  # the transition of system kinds is fixed
    leave.save()
    StatusChangeTypeSeeder()()

    leave.refresh_from_db()
    assert StudentStatusChangeType.objects.count() == 6
    assert leave.name_translations["en"] == "Leave"
    assert leave.can_student_request is False
    assert leave.to_status == StudentStatus.ON_LEAVE


def test_creates_demo_people_with_bulk_inserts_and_fixed_portal_accounts(essential_data: None) -> None:
    with use_options(DemoOptions(size="small", seed=42)):
        DemoReferenceSeeder()()
        DemoPeopleSeeder()()
        DemoPeopleSeeder()()  # runs once per database

    assert StudentRecord.objects.count() == 104  # 100 + student, alumni and two readmitted records
    assert Instructor.objects.filter(employee_number__startswith="DEMO-").count() == 20
    assert AdvisorAssignment.objects.exists()
    for email in DemoPeopleSeeder.emails():
        assert User.objects.filter(email=email).count() == 1

    resolver = PersonaResolver(registered_detectors())
    readmitted = User.objects.get(email="readmitted@demo.test")
    assert set(resolver.personas_for(readmitted)) == {Persona.STUDENT, Persona.ALUMNI}
    assert StudentRecord.objects.filter(person_id=readmitted.person_id).count() == 2
    assert set(resolver.personas_for(User.objects.get(email="instructor@demo.test"))) >= {
        Persona.INSTRUCTOR,
        Persona.ADVISOR,
    }
    assert set(resolver.personas_for(User.objects.get(email="alumni@demo.test"))) == {Persona.ALUMNI}


def test_draws_the_same_people_with_the_same_seed() -> None:
    today = date(2026, 10, 24)
    first = _Names(DemoOptions(size="tiny", seed=7).rng)
    second = _Names(DemoOptions(size="tiny", seed=7).rng)
    other = _Names(DemoOptions(size="tiny", seed=8).rng)

    names = [first.person(None, today).romanized_name() for _ in range(5)]
    assert names == [second.person(None, today).romanized_name() for _ in range(5)]
    assert names != [other.person(None, today).romanized_name() for _ in range(5)]


def test_setup_demo_writes_accounts_for_enrolled_students(essential_data: None) -> None:
    call_command("setup_demo", size="tiny", force=True, student_accounts=True, stdout=StringIO(), stderr=StringIO())

    enrolled = StudentRecord.objects.filter(status=StudentStatus.ENROLLED).values("person_id")
    assert (
        User.objects.filter(person_id__in=enrolled).count()
        == StudentRecord.objects.filter(status=StudentStatus.ENROLLED).values("person_id").distinct().count()
    )
