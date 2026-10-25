"""Who may read course evaluation rows in the database (original
``tests/Database/Evaluation/EvaluationAccessTest.php``): students see only their own completions,
never answers, and cannot write responses; instructors see their sections' answers only after the
term's results are published. Also: ``EvaluationResponse.objects.visible_to`` gives the same rows
as the row level security policies (``db/sql/policies/evaluations.sql``)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from django.db import connection
from django.utils import timezone

from ninefruits.core.db import session_context
from ninefruits.evaluation.models import (
    EvaluationAnswer,
    EvaluationCompletion,
    EvaluationResponse,
    TermEvaluation,
)
from ninefruits.offering.models import SectionInstructor
from ninefruits.security.enums import Permission, ScopeType
from tests.db.support import database_error
from tests.factories.evaluation import EvaluationQuestionFactory, TermEvaluationFactory
from tests.factories.offering import SectionFactory
from tests.factories.person import InstructorFactory, StudentRecordFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory

pytestmark = pytest.mark.django_db


def as_evaluation_user(user: Any) -> None:
    context = session_context()
    context.use_baseline({})
    context.for_user(user.pk)


def count(table: str) -> int:
    queries = {
        "evaluation_answers": "SELECT count(*) FROM evaluation_answers",
        "evaluation_responses": "SELECT count(*) FROM evaluation_responses",
        "evaluation_completions": "SELECT count(*) FROM evaluation_completions",
    }
    with connection.cursor() as cursor:
        cursor.execute(queries[table])
        return int(cursor.fetchone()[0])


@pytest.fixture
def world() -> dict[str, Any]:
    section = SectionFactory(published=True)
    question = EvaluationQuestionFactory(text={"en": "Q"})
    evaluation = TermEvaluationFactory(term=section.term, form=question.form)

    record = StudentRecordFactory()
    enrollment = EnrollmentFactory(section=section, student_record=record)
    student = UserFactory(person=record.person)
    EvaluationCompletion.objects.create(enrollment=enrollment, completed_at=timezone.now().replace(microsecond=0))
    response = EvaluationResponse.objects.create(term=section.term, section=section, form=question.form)
    EvaluationAnswer.objects.create(response=response, question=question, value=4)

    instructor = InstructorFactory()
    SectionInstructor.objects.create(section=section, instructor=instructor, role="primary")
    teacher = UserFactory(person=instructor.person)
    return {"section": section, "evaluation": evaluation, "student": student, "teacher": teacher}


def test_never_shows_answers_to_students_only_their_own_completion(world: dict[str, Any]) -> None:
    section, evaluation = world["section"], world["evaluation"]
    as_evaluation_user(world["student"])

    assert count("evaluation_answers") == 0
    assert count("evaluation_responses") == 0
    assert count("evaluation_completions") == 1

    def insert() -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO evaluation_responses (id, term_id, section_id, evaluation_form_id) "
                "VALUES (%s, %s, %s, %s)",
                [str(uuid.uuid4()), section.term_id, section.pk, evaluation.form_id],
            )

    assert "row-level security" in (database_error(insert) or "")


def test_shows_answers_to_the_instructor_only_after_publication(world: dict[str, Any]) -> None:
    as_evaluation_user(world["teacher"])
    assert count("evaluation_answers") == 0
    assert count("evaluation_completions") == 0

    TermEvaluation.objects.filter(pk=world["evaluation"].pk).update(results_published_at=timezone.now())

    assert count("evaluation_answers") == 1


def test_matches_row_level_security_in_visible_to(world: dict[str, Any]) -> None:
    section = world["section"]
    other = SectionFactory(term=section.term, published=True)
    EvaluationResponse.objects.create(term=section.term, section=other, form=world["evaluation"].form)
    TermEvaluation.objects.filter(pk=world["evaluation"].pk).update(results_published_at=timezone.now())
    users = [
        world["student"],
        world["teacher"],
        UserFactory(),
        UserFactory(permissions=[Permission.EVALUATIONS_VIEW]),
        UserFactory(permissions=[Permission.EVALUATIONS_MANAGE]),
        UserFactory(
            permissions=[Permission.EVALUATIONS_VIEW],
            permissions__scope_type=ScopeType.ORG_UNIT,
            permissions__scope_id=other.org_unit_id,
        ),
    ]
    context = session_context()
    for user in users:
        context.use_baseline({"app.actor": "system:test"})
        expected = sorted(str(pk) for pk in EvaluationResponse.objects.visible_to(user).values_list("pk", flat=True))
        as_evaluation_user(user)
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM evaluation_responses")
            seen = sorted(str(row[0]) for row in cursor.fetchall())
        assert seen == expected, user
    context.use_baseline({"app.actor": "system:test"})
