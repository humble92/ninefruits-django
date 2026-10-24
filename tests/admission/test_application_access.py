"""Original tests/Database/Admission/ApplicationAccessTest.php.

Who sees and changes which applications, checked in both layers independently: application
scope (``Application.objects.visible_to``, run as the system actor) and row level security
(plain queries as the user)."""

from __future__ import annotations

from typing import Any

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from ninefruits.admission.models import Application
from ninefruits.core.db import session_context
from ninefruits.person.models import Person
from ninefruits.security.actions import AssignRole
from ninefruits.security.enums import Permission, ScopeType
from ninefruits.security.services.authorization import authorization
from tests.factories.admission import AdmissionCycleFactory, ApplicationFactory
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.person import PersonFactory
from tests.factories.security import RoleFactory, UserFactory

pytestmark = pytest.mark.django_db

VIEWERS = {
    "admissions office": ["A-CSE", "A-KOR"],
    "engineering reviewer (college includes departments)": ["A-CSE"],
    "korean program viewer": ["A-KOR"],
    "applicant": ["A-CSE"],
    "user without roles": [],
}
USERS = {
    "admissions office": "admissions office",
    "engineering reviewer (college includes departments)": "engineering reviewer",
    "korean program viewer": "korean program viewer",
    "applicant": "cse applicant",
    "user without roles": "nobody",
}


@pytest.fixture
def world() -> dict[str, Any]:
    eng = OrgUnitFactory(code="ENG")
    cse = OrgUnitFactory(code="CSE", parent=eng)
    kor = OrgUnitFactory(code="KOR")
    cse_program = ProgramFactory(code="B-CSE", org_unit=cse)
    kor_program = ProgramFactory(code="B-KOR", org_unit=kor)
    cycle = AdmissionCycleFactory()

    def apply(number: str, program: Any) -> Application:
        application = ApplicationFactory(admission_cycle=cycle, program=program, submitted=True, person=PersonFactory())
        application.application_number = number
        application.save()
        return application

    cse_application = apply("A-CSE", cse_program)
    kor_application = apply("A-KOR", kor_program)

    def assigned(permissions: list[Permission], scope_type: ScopeType = ScopeType.GLOBAL, scope_id: int | None = None):  # type: ignore[no-untyped-def]
        user = UserFactory()
        AssignRole()(user, RoleFactory(permissions=permissions), "test", scope_type, scope_id)
        return user

    users = {
        "admissions office": assigned([Permission.APPLICATIONS_REVIEW]),
        "engineering reviewer": assigned([Permission.APPLICATIONS_REVIEW], ScopeType.ORG_UNIT, eng.pk),
        "korean program viewer": assigned([Permission.APPLICATIONS_VIEW], ScopeType.PROGRAM, kor_program.pk),
        "cse applicant": UserFactory(person=cse_application.person),
        "nobody": UserFactory(),
    }
    authorization().flush()
    return {"users": users, "cse": cse_application, "kor": kor_application}


def _rows(sql: str, params: list[Any] | None = None) -> list[Any]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        return [row[0] for row in cursor.fetchall()]


def _update(sql: str, params: list[Any]) -> int:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return int(cursor.rowcount)


@pytest.mark.parametrize(("who", "expected"), VIEWERS.items(), ids=list(VIEWERS))
def test_limits_applications_in_the_application_layer(world: dict[str, Any], who: str, expected: list[str]) -> None:
    user = world["users"][USERS[who]]
    visible = Application.objects.visible_to(user).order_by("application_number")
    assert list(visible.values_list("application_number", flat=True)) == expected


@pytest.mark.parametrize(("who", "expected"), VIEWERS.items(), ids=list(VIEWERS))
def test_limits_applications_and_applicants_in_the_database_for_the_same_users(
    world: dict[str, Any], who: str, expected: list[str]
) -> None:
    user = world["users"][USERS[who]]
    # The application layer's person scope agrees with the database below.
    people_in_scope = set(Person.objects.visible_to(user).values_list("pk", flat=True))
    context = session_context()
    context.use_baseline({})
    context.for_user(user.pk)

    assert _rows("SELECT application_number FROM applications ORDER BY application_number") == expected
    people = set(_rows("SELECT id FROM people"))
    for key, number in (("cse", "A-CSE"), ("kor", "A-KOR")):
        person_id = world[key].person_id
        assert (person_id in people) == (number in expected)
        assert (person_id in people_in_scope) == (number in expected)


def test_does_not_let_applicants_decide_their_own_application_in_the_database(world: dict[str, Any]) -> None:
    users, cse, kor = world["users"], world["cse"], world["kor"]
    context = session_context()
    context.use_baseline({})
    context.for_user(users["cse applicant"].pk)

    # Own savepoint: the refused statement would otherwise abort the test transaction.
    with pytest.raises(DatabaseError, match="row-level security"), transaction.atomic():
        _update("UPDATE applications SET status = 'admitted' WHERE id = %s", [cse.pk])

    assert (
        _update(
            "UPDATE applications SET status = 'withdrawn', withdrawn_at = %s WHERE id = %s", [timezone.now(), cse.pk]
        )
        == 1
    )

    context.for_user(users["korean program viewer"].pk)
    assert _update("UPDATE applications SET status = 'admitted' WHERE id = %s", [kor.pk]) == 0

    context.for_user(users["engineering reviewer"].pk)
    assert _update("UPDATE applications SET decision_note = 'ok' WHERE id = %s", [cse.pk]) == 1
    assert _update("UPDATE applications SET decision_note = 'ok' WHERE id = %s", [kor.pk]) == 0
