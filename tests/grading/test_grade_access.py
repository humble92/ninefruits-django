"""Who may write and read grades in the database (original
``tests/Database/Grading/GradeAccessTest.php``): instructors write draft and submitted grades of
their own sections only, cannot finalize, and request changes only for their sections. Also:
``visible_to`` of term records and grade change requests gives the same rows as the row level
security policies (``db/sql/policies/grading.sql``)."""

from __future__ import annotations

from typing import Any

import pytest
from django.db import connection
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.grading.models import GradeChangeRequest, TermRecord
from ninefruits.offering.models import SectionInstructor
from ninefruits.security.enums import Permission, ScopeType
from ninefruits.security.services.authorization import authorization
from tests.db.support import database_error
from tests.factories.curriculum import CourseFactory
from tests.factories.offering import SectionFactory
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.person import InstructorFactory, StudentRecordFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory

pytestmark = pytest.mark.django_db


def as_database_user(user: Any) -> None:
    context = session_context()
    context.use_baseline({})
    context.for_user(user.pk)


def execute(sql: str, params: list[Any]) -> int:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return int(cursor.rowcount)


@pytest.fixture
def teaching(korean_scale: Any) -> dict[str, Any]:
    mine = EnrollmentFactory(section=SectionFactory(published=True))
    theirs = EnrollmentFactory(section=SectionFactory(published=True))
    instructor = InstructorFactory()
    SectionInstructor.objects.create(section=mine.section, instructor=instructor, role="primary")
    teacher = UserFactory(person=instructor.person)
    scale_id = EnrollmentFactory(grade="A0").grade_scale_id
    as_database_user(teacher)
    return {"mine": mine, "theirs": theirs, "teacher": teacher, "scale_id": scale_id}


def draft(world: dict[str, Any], enrollment: Any) -> int:
    return execute(
        "UPDATE enrollments SET grade_status = 'draft', grade_code = 'A0', grade_scale_id = %s WHERE id = %s",
        [world["scale_id"], enrollment.pk],
    )


def test_lets_an_instructor_write_draft_and_submitted_grades_of_their_own_sections_only(
    teaching: dict[str, Any],
) -> None:
    mine, theirs = teaching["mine"], teaching["theirs"]
    assert draft(teaching, mine) == 1
    assert draft(teaching, theirs) == 0
    assert execute("UPDATE enrollments SET grade_status = 'submitted' WHERE id = %s", [mine.pk]) == 1
    # Submitted grades are out of the instructor's reach.
    assert execute("UPDATE enrollments SET grade_code = 'F' WHERE id = %s", [mine.pk]) == 0


def test_does_not_let_an_instructor_finalize(teaching: dict[str, Any]) -> None:
    mine = teaching["mine"]
    draft(teaching, mine)
    error = database_error(
        lambda: execute(
            "UPDATE enrollments SET grade_status = 'finalized', status = 'completed' WHERE id = %s", [mine.pk]
        )
    )
    assert error is not None and "row-level security" in error


def test_lets_the_instructor_request_a_change_for_their_section_and_nobody_else_for_theirs(
    teaching: dict[str, Any],
) -> None:
    def request(enrollment: Any) -> str | None:
        return database_error(
            lambda: execute(
                "INSERT INTO grade_change_requests (enrollment_id, to_grade_code, reason, status, requested_by_id, "
                "requested_at, created_at, updated_at) VALUES (%s, 'A0', 'x', 'pending', %s, now(), now(), now())",
                [enrollment.pk, teaching["teacher"].pk],
            )
        )

    assert request(teaching["mine"]) is None
    error = request(teaching["theirs"])
    assert error is not None and "row-level security" in error


# -- application scope = row level security -----------------------------------------------------
@pytest.fixture
def world(korean_scale: Any) -> dict[str, Any]:
    cse, kor = OrgUnitFactory(code="CSE"), OrgUnitFactory(code="KOR")
    cse_section = SectionFactory(published=True, course=CourseFactory(org_unit=cse))
    kor_section = SectionFactory(published=True, course=CourseFactory(org_unit=kor))
    alice = StudentRecordFactory(program=ProgramFactory(org_unit=cse))
    bob = StudentRecordFactory(program=ProgramFactory(org_unit=kor))
    rows: dict[str, list[Any]] = {"term_records": [], "grade_change_requests": []}
    requester = UserFactory()
    for record, section in ((alice, cse_section), (bob, kor_section)):
        enrollment = EnrollmentFactory(student_record=record, section=section, grade="B0")
        rows["term_records"].append(
            TermRecord.objects.create(student_record=record, term=section.term, calculated_at=timezone.now())
        )
        rows["grade_change_requests"].append(
            GradeChangeRequest.objects.create(
                enrollment=enrollment,
                from_grade_code="B0",
                to_grade_code="A0",
                reason="Test",
                requested_by=requester,
                requested_at=timezone.now(),
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
        "registrar": scoped(Permission.GRADES_MANAGE),
        "grade viewer": scoped(Permission.GRADES_VIEW),
        "cse grade viewer": scoped(Permission.GRADES_VIEW, cse),
        "student records officer": scoped(Permission.STUDENT_RECORDS_VIEW),
        "kor instructor": UserFactory(person=instructor.person),
        "requester": requester,
        "nobody": UserFactory(),
    }
    authorization().flush()
    return {"users": users, "rows": rows}


def _database_ids(table: str) -> set[int]:
    with connection.cursor() as cursor:
        cursor.execute(
            {
                "term_records": "SELECT id FROM term_records",
                "grade_change_requests": "SELECT id FROM grade_change_requests",
            }[table]
        )
        return {row[0] for row in cursor.fetchall()}


MODELS = {"term_records": TermRecord, "grade_change_requests": GradeChangeRequest}


@pytest.mark.parametrize(
    "who",
    [
        "alice",
        "bob",
        "registrar",
        "grade viewer",
        "cse grade viewer",
        "student records officer",
        "kor instructor",
        "requester",
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
    as_database_user(user)
    database = {name: _database_ids(name) & created[name] for name in MODELS}

    assert application == database
