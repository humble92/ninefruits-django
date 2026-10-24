"""Who sees which registrations (ADR 0010 "행 수준 보안"): ``visible_to`` and the row level
security policies of ``db/sql/policies/registration.sql`` give the same rows, checked
independently (application scope run as the system; plain queries as the user). Students change
only their own registration status, and only in the ways the policies allow."""

from __future__ import annotations

from typing import Any

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.offering.models import SectionInstructor
from ninefruits.registration.enums import AttemptAction, AttemptOutcome
from ninefruits.registration.models import (
    CartItem,
    Enrollment,
    RegistrationAttempt,
    RegistrationHold,
    RegistrationOverride,
    WaitlistEntry,
)
from ninefruits.security.enums import Permission, ScopeType
from ninefruits.security.services.authorization import authorization
from tests.factories.curriculum import CourseFactory
from tests.factories.offering import SectionFactory
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.person import InstructorFactory, StudentRecordFactory
from tests.factories.registration import EnrollmentFactory, RegistrationHoldFactory, WaitlistEntryFactory
from tests.factories.security import UserFactory

pytestmark = pytest.mark.django_db

MODELS = {
    "enrollments": Enrollment,
    "waitlist_entries": WaitlistEntry,
    "cart_items": CartItem,
    "registration_holds": RegistrationHold,
    "registration_overrides": RegistrationOverride,
    "registration_attempts": RegistrationAttempt,
}


@pytest.fixture
def world() -> dict[str, Any]:
    cse, kor = OrgUnitFactory(code="CSE"), OrgUnitFactory(code="KOR")
    cse_section = SectionFactory(published=True, course=CourseFactory(org_unit=cse))
    kor_section = SectionFactory(published=True, course=CourseFactory(org_unit=kor))
    alice = StudentRecordFactory(program=ProgramFactory(org_unit=cse))
    bob = StudentRecordFactory(program=ProgramFactory(org_unit=kor))
    rows: dict[str, list[Any]] = {name: [] for name in MODELS}
    for record, section in ((alice, cse_section), (bob, kor_section)):
        rows["enrollments"].append(EnrollmentFactory(student_record=record, section=section))
        rows["waitlist_entries"].append(
            WaitlistEntryFactory(student_record=record, section=cse_section if section == kor_section else kor_section)
        )
        rows["cart_items"].append(CartItem.objects.create(student_record=record, term=section.term, section=section))
        rows["registration_holds"].append(RegistrationHoldFactory(student_record=record))
        rows["registration_overrides"].append(
            RegistrationOverride.objects.create(
                student_record=record, term=section.term, rule_code="credit_limit", reason="Test"
            )
        )
        rows["registration_attempts"].append(
            RegistrationAttempt.objects.create(
                student_record=record,
                section=section,
                term=section.term,
                action=AttemptAction.ENROLL,
                outcome=AttemptOutcome.REFUSED,
                results=[],
                attempted_at=timezone.now(),
            )
        )
    instructor = InstructorFactory(org_unit=kor)
    SectionInstructor.objects.create(section=kor_section, instructor=instructor)

    def scoped(permission: Permission, unit: Any | None = None) -> Any:
        if unit is None:
            return UserFactory(permissions=[permission])
        return UserFactory(
            permissions=[permission], permissions__scope_type=ScopeType.ORG_UNIT, permissions__scope_id=unit.pk
        )

    users = {
        "alice": UserFactory(person=alice.person),
        "bob": UserFactory(person=bob.person),
        "registrar": scoped(Permission.REGISTRATION_MANAGE),
        "cse registration assistant": scoped(Permission.REGISTRATION_MANAGE, cse),
        "roster viewer": scoped(Permission.ENROLLMENTS_VIEW),
        "kor hold officer": scoped(Permission.REGISTRATION_HOLDS_MANAGE, kor),
        "kor instructor": UserFactory(person=instructor.person),
        "nobody": UserFactory(),
    }
    authorization().flush()
    return {"users": users, "rows": rows}


def _database_ids(table: str) -> set[int]:
    with connection.cursor() as cursor:
        cursor.execute(
            {
                "enrollments": "SELECT id FROM enrollments",
                "waitlist_entries": "SELECT id FROM waitlist_entries",
                "cart_items": "SELECT id FROM cart_items",
                "registration_holds": "SELECT id FROM registration_holds",
                "registration_overrides": "SELECT id FROM registration_overrides",
                "registration_attempts": "SELECT id FROM registration_attempts",
            }[table]
        )
        return {row[0] for row in cursor.fetchall()}


@pytest.mark.parametrize(
    "who",
    [
        "alice",
        "bob",
        "registrar",
        "cse registration assistant",
        "roster viewer",
        "kor hold officer",
        "kor instructor",
        "nobody",
    ],
)
def test_application_scope_and_row_level_security_agree(world: dict[str, Any], who: str) -> None:
    user = world["users"][who]
    created = {name: {row.pk for row in rows} for name, rows in world["rows"].items()}
    application = {
        name: set(model.objects.visible_to(user).filter(pk__in=created[name]).values_list("pk", flat=True))
        for name, model in MODELS.items()
    }

    context = session_context()
    context.use_baseline({})
    context.for_user(user.pk)
    database = {name: _database_ids(name) & created[name] for name in MODELS}

    assert application == database


def test_students_see_only_their_own_registrations(world: dict[str, Any]) -> None:
    alice = world["users"]["alice"]
    own = world["rows"]["enrollments"][0]
    assert set(Enrollment.objects.visible_to(alice).values_list("pk", flat=True)) == {own.pk}


def test_a_student_can_only_drop_their_own_registration_and_not_grade_it(world: dict[str, Any]) -> None:
    alice_enrollment, bob_enrollment = world["rows"]["enrollments"]
    context = session_context()
    context.use_baseline({})
    context.for_user(world["users"]["alice"].pk)

    def update(sql: str, params: list[Any]) -> int:
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(sql, params)
            return int(cursor.rowcount)

    assert update("UPDATE enrollments SET status = 'dropped' WHERE id = %s", [bob_enrollment.pk]) == 0
    with pytest.raises(DatabaseError):
        update("UPDATE enrollments SET grade_code = 'A+' WHERE id = %s", [alice_enrollment.pk])
    assert update("UPDATE enrollments SET status = 'dropped' WHERE id = %s", [alice_enrollment.pk]) == 1
