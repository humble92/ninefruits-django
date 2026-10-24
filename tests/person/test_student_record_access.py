"""Original tests/Database/Person/StudentRecordAccessTest.php.

Phase 2 completion criterion: who sees which student records and people, checked in both layers
independently (porting-plan 7.4):

- application: ``StudentRecord.objects.visible_to()`` run as the system actor (RLS passes all);
- database: plain queries as the user (no application scope)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.db import connection
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.person.actions import AssignAdvisor
from ninefruits.person.models import StudentRecord
from ninefruits.security.actions import AssignRole
from ninefruits.security.enums import Permission, ScopeType
from ninefruits.security.services.authorization import authorization
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.person import InstructorFactory, StudentRecordFactory
from tests.factories.security import RoleFactory, UserFactory

pytestmark = pytest.mark.django_db

VIEWERS = {
    "registrar": ["S-ALICE", "S-BOB", "S-CAROL"],
    "cse assistant": ["S-ALICE"],
    "engineering assistant": ["S-ALICE", "S-BOB"],
    "korean program officer": ["S-CAROL"],
    "advisor": ["S-CAROL"],
    "alice": ["S-ALICE"],
    "nobody": [],
}


@pytest.fixture
def world() -> dict[str, Any]:
    eng = OrgUnitFactory(code="ENG")
    cse = OrgUnitFactory(code="CSE", parent=eng)
    ee = OrgUnitFactory(code="EE", parent=eng)
    kor = OrgUnitFactory(code="KOR")
    programs = {
        "CSE": ProgramFactory(code="B-CSE", org_unit=cse),
        "EE": ProgramFactory(code="B-EE", org_unit=ee),
        "KOR": ProgramFactory(code="B-KOR", org_unit=kor),
    }
    records = {
        "alice": StudentRecordFactory(student_number="S-ALICE", program=programs["CSE"]),
        "bob": StudentRecordFactory(student_number="S-BOB", program=programs["EE"]),
        "carol": StudentRecordFactory(student_number="S-CAROL", program=programs["KOR"]),
    }
    view = RoleFactory(permissions=[Permission.STUDENT_RECORDS_VIEW])

    def assigned(scope_type: ScopeType = ScopeType.GLOBAL, scope_id: int | None = None) -> Any:
        user = UserFactory()
        AssignRole()(user, view, "test", scope_type, scope_id)
        return user

    users = {
        "registrar": assigned(),
        "cse assistant": assigned(ScopeType.ORG_UNIT, cse.pk),
        "engineering assistant": assigned(ScopeType.ORG_UNIT, eng.pk),
        "korean program officer": assigned(ScopeType.PROGRAM, programs["KOR"].pk),
        "alice": UserFactory(person=records["alice"].person),
        "nobody": UserFactory(),
    }
    advisor = InstructorFactory(org_unit=cse)
    users["advisor"] = UserFactory(person=advisor.person)
    AssignAdvisor().handle(records["carol"], advisor, timezone.localdate() - timedelta(days=30))
    authorization().flush()
    return {"users": users, "records": records}


def _rows(sql: str, params: list[Any] | None = None) -> list[Any]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return [row[0] for row in cursor.fetchall()]


@pytest.mark.parametrize(("who", "expected"), VIEWERS.items(), ids=list(VIEWERS))
def test_limits_student_records_in_the_application_layer(world: dict[str, Any], who: str, expected: list[str]) -> None:
    visible = StudentRecord.objects.visible_to(world["users"][who]).order_by("student_number")
    assert list(visible.values_list("student_number", flat=True)) == expected


@pytest.mark.parametrize(("who", "expected"), VIEWERS.items(), ids=list(VIEWERS))
def test_limits_student_records_in_the_database_for_the_same_users(
    world: dict[str, Any], who: str, expected: list[str]
) -> None:
    context = session_context()
    context.use_baseline({})
    context.for_user(world["users"][who].pk)

    assert _rows("SELECT student_number FROM student_records ORDER BY student_number") == expected
    person_ids = set(_rows("SELECT id FROM people"))
    for name, record in world["records"].items():
        assert (record.person_id in person_ids) == (record.student_number in expected), name


def test_lets_only_scoped_managers_change_a_record_in_the_database(world: dict[str, Any]) -> None:
    alice, bob = world["records"]["alice"], world["records"]["bob"]
    manager = UserFactory()
    AssignRole()(
        manager,
        RoleFactory(permissions=[Permission.STUDENT_RECORDS_MANAGE]),
        "test",
        ScopeType.ORG_UNIT,
        alice.org_unit_id,
    )

    context = session_context()
    context.use_baseline({})
    context.for_user(manager.pk)

    def update(record_id: int, level: int) -> int:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE student_records SET year_level = %s WHERE id = %s", [level, record_id])
            return int(cursor.rowcount)

    assert update(alice.pk, 2) == 1
    assert update(bob.pk, 2) == 0

    context.for_user(world["users"]["cse assistant"].pk)
    assert update(alice.pk, 3) == 0


def test_hides_people_from_other_people_unless_a_rule_allows_it(world: dict[str, Any]) -> None:
    users, records = world["users"], world["records"]
    context = session_context()
    context.use_baseline({})
    context.for_user(users["alice"].pk)

    def exists(person_id: int) -> bool:
        return bool(_rows("SELECT id FROM people WHERE id = %s", [person_id]))

    assert not exists(records["bob"].person_id)
    assert exists(records["alice"].person_id)
    assert exists(users["advisor"].person_id)
