"""Who sees and writes registrations, results and corrections in the database
(``db/sql/policies/assessments.sql``, ``assessment_corrections.sql``), and ``visible_to`` of the
models gives the same rows as row level security for students, staff in different scopes and
users without a role."""

from __future__ import annotations

from typing import Any

import pytest
from django.db import connection
from django.utils import timezone

from ninefruits.assessment.models import (
    AssessmentComponentScore,
    AssessmentRegistration,
    AssessmentResult,
    AssessmentResultCorrection,
)
from ninefruits.core.db import session_context
from ninefruits.security.enums import Permission, ScopeType
from ninefruits.security.services.authorization import authorization
from tests.factories.assessment import (
    AssessmentComponentFactory,
    AssessmentRegistrationFactory,
    AssessmentResultFactory,
    AssessmentSessionFactory,
)
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory

pytestmark = pytest.mark.django_db

TABLES = {
    "assessment_registrations": AssessmentRegistration,
    "assessment_results": AssessmentResult,
    "assessment_component_scores": AssessmentComponentScore,
    "assessment_result_corrections": AssessmentResultCorrection,
}
SQL = {
    "assessment_registrations": "SELECT id FROM assessment_registrations",
    "assessment_results": "SELECT id FROM assessment_results",
    "assessment_component_scores": "SELECT id FROM assessment_component_scores",
    "assessment_result_corrections": "SELECT id FROM assessment_result_corrections",
}


def as_database_user(user: Any) -> None:
    context = session_context()
    context.use_baseline({})
    context.for_user(user.pk)


def _database_ids(table: str) -> set[int]:
    with connection.cursor() as cursor:
        cursor.execute(SQL[table])
        return {row[0] for row in cursor.fetchall()}


@pytest.fixture
def world(essential_data: None) -> dict[str, Any]:
    cse, kor = OrgUnitFactory(), OrgUnitFactory()
    alice = StudentRecordFactory(program=ProgramFactory(org_unit=cse))
    bob = StudentRecordFactory(program=ProgramFactory(org_unit=kor))
    published = AssessmentSessionFactory(published=True)
    unpublished = AssessmentSessionFactory(assessment_type=published.assessment_type)
    component = AssessmentComponentFactory(assessment_type=published.assessment_type)
    requester = UserFactory(permissions=[Permission.ASSESSMENTS_RECORD])
    rows: dict[str, list[Any]] = {name: [] for name in TABLES}
    for record in (alice, bob):
        for session in (published, unpublished):
            registration = AssessmentRegistrationFactory(session=session, student_record=record)
            result = AssessmentResultFactory(registration=registration)
            rows["assessment_registrations"].append(registration)
            rows["assessment_results"].append(result)
            rows["assessment_component_scores"].append(
                AssessmentComponentScore.objects.create(result=result, component=component, score=20)
            )
            rows["assessment_result_corrections"].append(
                AssessmentResultCorrection.objects.create(
                    result=result,
                    proposed={"total": 80},
                    previous={"total": 70},
                    reason="Test",
                    requested_by=requester,
                    requested_at=timezone.now(),
                )
            )
        rows["assessment_results"].append(AssessmentResultFactory(external=True, student_record=record))

    def scoped(*permissions: Permission, unit: Any | None = None) -> Any:
        if unit is None:
            return UserFactory(permissions=list(permissions))
        return UserFactory(
            permissions=list(permissions), permissions__scope_type=ScopeType.ORG_UNIT, permissions__scope_id=unit.pk
        )

    users = {
        "alice": UserFactory(person=alice.person),
        "bob": UserFactory(person=bob.person),
        "recorder": scoped(Permission.ASSESSMENTS_RECORD, Permission.STUDENT_RECORDS_VIEW),
        "manager": scoped(Permission.ASSESSMENTS_MANAGE, Permission.STUDENT_RECORDS_VIEW),
        "cse recorder": scoped(Permission.ASSESSMENTS_RECORD, Permission.STUDENT_RECORDS_VIEW, unit=cse),
        "records officer": scoped(Permission.STUDENT_RECORDS_VIEW),
        "requester": requester,
        "nobody": UserFactory(),
    }
    authorization().flush()
    return {"users": users, "rows": rows}


@pytest.mark.parametrize(
    "who", ["alice", "bob", "recorder", "manager", "cse recorder", "records officer", "requester", "nobody"]
)
def test_application_scope_and_row_level_security_agree(world: dict[str, Any], who: str) -> None:
    user = world["users"][who]
    created = {name: {row.pk for row in rows} for name, rows in world["rows"].items()}
    application = {
        name: set(model.objects.visible_to(user).filter(pk__in=created[name]).values_list("pk", flat=True))
        for name, model in TABLES.items()
    }
    as_database_user(user)
    database = {name: _database_ids(name) & created[name] for name in TABLES}

    assert application == database


def test_a_student_sees_own_published_and_external_results_only(world: dict[str, Any]) -> None:
    alice = world["users"]["alice"]
    as_database_user(alice)
    results = list(AssessmentResult.objects.all())
    assert len(results) == 2
    assert {result.source for result in results} == {"session", "external"}
    # Students never write results (no write policy).
    with connection.cursor() as cursor:
        cursor.execute("UPDATE assessment_results SET is_passed = false")
        assert cursor.rowcount == 0
        cursor.execute("UPDATE assessment_registrations SET status = 'absent'")
        assert cursor.rowcount == 0


def test_staff_write_results_only_with_the_record_permission(world: dict[str, Any]) -> None:
    for who, expected in (("recorder", 4), ("manager", 0), ("records officer", 0)):
        as_database_user(world["users"][who])
        with connection.cursor() as cursor:
            cursor.execute("UPDATE assessment_results SET note = 'checked' WHERE source = 'session'")
            assert cursor.rowcount == expected, who
