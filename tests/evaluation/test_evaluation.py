"""Course evaluation for students and instructors (original
``tests/Feature/Evaluation/EvaluationTest.php``): anonymous responses apart from completions,
refusals, what is evaluated, uniform answers, grades hidden while the evaluation is open, results
only when published and with enough responses, and the student portal. Actions run with the
acting user's database context (row level security applies, like a real request)."""

from __future__ import annotations

import re
import uuid
from datetime import timedelta
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection

from ninefruits.evaluation.actions import ManageTermEvaluation, SubmitEvaluation
from ninefruits.evaluation.models import (
    EvaluationAnswer,
    EvaluationCompletion,
    EvaluationResponse,
)
from ninefruits.evaluation.services import EvaluationResults, EvaluationTasks
from ninefruits.registration.enums import EnrollmentStatus
from tests.factories.evaluation import EvaluationQuestionFactory
from tests.factories.offering import SectionFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory

from .conftest import World, now, set_evaluation, signed_in

pytestmark = pytest.mark.django_db


def submit(as_user: Any, enrollment: Any, answers: dict[Any, Any], student: Any) -> None:
    with as_user(student):
        SubmitEvaluation()(enrollment, answers, student)


def response_columns() -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' "
            "AND table_name = 'evaluation_responses'"
        )
        return sorted(row[0] for row in cursor.fetchall())


def audited_rows() -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM audit.record_changes WHERE table_name IN "
            "('evaluation_responses', 'evaluation_answers', 'evaluation_completions')"
        )
        return int(cursor.fetchone()[0])


def test_records_who_evaluated_apart_from_what_they_answered(world: World, as_user: Any) -> None:
    enrollment, student = world.student()

    submit(as_user, enrollment, world.answers(comment="Great examples"), student)

    response = EvaluationResponse.objects.get()
    assert EvaluationCompletion.objects.get().enrollment_id == enrollment.pk
    # No student, no sequence, no time: a random (v4) UUID and the section.
    assert response_columns() == ["evaluation_form_id", "id", "section_id", "term_id"]
    assert uuid.UUID(str(response.pk)).version == 4
    assert dict(response.answers.values_list("question_id", "value")) == {
        world.clear.pk: 4,
        world.hard.pk: 2,
        world.comment.pk: None,
    }
    # Responses are not audited row by row: the data audit records the acting user.
    assert audited_rows() == 0

    with pytest.raises(ValidationError, match=re.escape("You have already evaluated this course.")):
        submit(as_user, enrollment, world.answers(), student)


def test_refuses_evaluations_outside_the_window_of_others_incomplete_or_out_of_range(
    world: World, as_user: Any
) -> None:
    enrollment, student = world.student()

    with pytest.raises(PermissionDenied):
        submit(as_user, enrollment, world.answers(), UserFactory())
    with pytest.raises(ValidationError, match=r"Answer every required question \(1 missing\)"):
        submit(as_user, enrollment, {world.clear.pk: 4}, student)
    with pytest.raises(ValidationError, match=re.escape("An answer is not valid.")):
        submit(as_user, enrollment, world.answers(clear=6), student)
    with pytest.raises(ValidationError, match=re.escape("An answer is not valid.")):
        submit(as_user, enrollment, world.answers(clear="4.5"), student)  # type: ignore[arg-type]

    world.window.closes_at = now() - timedelta(minutes=1)
    world.window.save(update_fields=["closes_at"])
    with pytest.raises(ValidationError, match=re.escape("The course evaluation is not open for this course.")):
        submit(as_user, enrollment, world.answers(), student)
    assert EvaluationResponse.objects.count() == 0


def test_leaves_out_withdrawn_courses_and_courses_that_are_not_evaluated(world: World) -> None:
    withdrawn, _student = world.student()
    withdrawn.status = EnrollmentStatus.WITHDRAWN
    withdrawn.save(update_fields=["status"])
    internship = SectionFactory(term=world.term, published=True)
    internship.version.requires_evaluation = False
    internship.version.save(update_fields=["requires_evaluation"])
    EnrollmentFactory(section=internship, student_record=withdrawn.student_record)

    assert EvaluationTasks().open(withdrawn.student_record) == []


def test_refuses_identical_answers_to_every_question_when_set(world: World, as_user: Any) -> None:
    set_evaluation(reject_uniform_answers=True)
    third = EvaluationQuestionFactory(form=world.form, sort_order=4, text={"en": "Fair"})
    enrollment, student = world.student()

    with pytest.raises(ValidationError, match=re.escape("Every answer is the same. Please answer each question.")):
        submit(as_user, enrollment, {**world.answers(5, 5), third.pk: 5}, student)

    # Off (the default): accepted.
    set_evaluation(reject_uniform_answers=False)
    submit(as_user, enrollment, {**world.answers(5, 5), third.pk: 5}, student)
    assert EvaluationResponse.objects.count() == 1


def test_hides_the_term_grades_until_the_evaluation_is_done_or_closed(
    world: World, as_user: Any, korean_scale: Any
) -> None:
    enrollment, student = world.student(grade="A0")
    code = enrollment.section.course.code
    tasks = EvaluationTasks()
    hidden = f"The grades of {world.term.name} show after you finish its course evaluation."

    assert tasks.blocked_term_ids(enrollment.student_record) == [world.term.pk]
    content = signed_in(student).get("/portal/grades/").content.decode()
    assert hidden in content
    assert code not in content
    assert "/portal/evaluations/" in content
    assert signed_in(student).get("/portal/grades/transcript/").content.decode().count(code) == 0

    submit(as_user, enrollment, world.answers(), student)
    assert tasks.blocked_term_ids(enrollment.student_record) == []
    assert code in signed_in(student).get("/portal/grades/").content.decode()
    assert code in signed_in(student).get("/portal/grades/transcript/").content.decode()

    # Unfinished, but the window closed: the grades show (the legacy lock never ended).
    other, _other_student = world.student()
    assert tasks.blocked_term_ids(other.student_record) == [world.term.pk]
    assert tasks.blocked_term_ids(other.student_record, now() + timedelta(weeks=2)) == []

    set_evaluation(grades_require_evaluation=False)
    assert EvaluationTasks().blocked_term_ids(other.student_record) == []


def test_shows_results_only_when_published_and_with_enough_responses_reversing_negative_questions(
    world: World, as_user: Any
) -> None:
    results = EvaluationResults()
    first, first_student = world.student()
    second, second_student = world.student()
    world.student()  # did not answer
    submit(as_user, first, world.answers(5, 1, "Clear and kind"), first_student)

    assert results.can_view(world.section, world.teacher) is False
    result = results.for_section(world.section)
    assert (result.shown, result.responses, result.expected) == (False, 1, 3)

    ManageTermEvaluation().publish(world.evaluation, None)
    assert results.for_section(world.section).shown is False  # 1 of minimum 2

    submit(as_user, second, world.answers(3, 3), second_student)
    result = results.for_section(world.section)

    assert results.can_view(world.section, world.teacher) is True
    assert results.can_view(SectionFactory(term=world.term, published=True), world.teacher) is False
    assert result.shown is True
    assert result.rate_percent == 66
    assert result.questions[world.clear.pk].mean == 4.0
    # Reversed: 1 counts as 5 and 3 as 3.
    assert result.questions[world.hard.pk].mean == 4.0
    assert result.questions[world.hard.pk].distribution == {1: 0, 2: 0, 3: 1, 4: 0, 5: 1}
    assert result.comments[world.comment.pk] == ["Clear and kind"]
    assert result.overall_mean == 4.0

    # The instructor's results page (with the instructor's database context).
    response = signed_in(world.teacher).get(f"/portal/sections/{world.section.pk}/evaluation/")
    assert response.status_code == 200
    assert "Clear and kind" in response.content.decode()
    assert signed_in(first_student).get(f"/portal/sections/{world.section.pk}/evaluation/").status_code == 403


def test_hides_answers_from_staff_until_published_and_escapes_comments(world: World, as_user: Any) -> None:
    from ninefruits.security.enums import Permission

    staff = UserFactory(permissions=[Permission.EVALUATIONS_VIEW, Permission.ENROLLMENTS_VIEW])
    students = [world.student() for _ in range(2)]
    for enrollment, student in students:
        submit(as_user, enrollment, world.answers(comment="<script>alert(1)</script>"), student)

    page = signed_in(staff).get(f"/portal/sections/{world.section.pk}/evaluation/").content.decode()
    assert "2 of 2 responded (100%)" in page
    assert "The results are not published yet." in page
    assert "alert(1)" not in page

    ManageTermEvaluation().publish(world.evaluation, None)
    page = signed_in(staff).get(f"/portal/sections/{world.section.pk}/evaluation/").content.decode()
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<script>alert(1)</script>" not in page


def test_shows_the_results_link_on_the_teaching_page_once_published(world: World) -> None:
    page = signed_in(world.teacher).get(f"/portal/teaching/?term={world.term.pk}").content.decode()
    assert "Course evaluation results" in page
    assert f"/portal/sections/{world.section.pk}/evaluation/" not in page
    assert "Not published" in page

    ManageTermEvaluation().publish(world.evaluation, None)
    page = signed_in(world.teacher).get(f"/portal/teaching/?term={world.term.pk}").content.decode()
    assert f"/portal/sections/{world.section.pk}/evaluation/" in page


def test_lets_the_student_evaluate_from_the_portal(world: World) -> None:
    enrollment, student = world.student()
    client = signed_in(student)

    page = client.get("/portal/evaluations/").content.decode()
    assert "Evaluate" in page
    assert "Course evaluation" in page
    page = client.get(f"/portal/evaluations/?enrollment={enrollment.pk}").content.decode()
    assert "Too hard" in page

    # Missing a required answer: the questionnaire again with what was entered.
    response = client.post("/portal/evaluations/", {"enrollment_id": enrollment.pk, f"answer-{world.clear.pk}": "4"})
    assert response.status_code == 200
    page = response.content.decode()
    assert "Answer every required question (1 missing)." in page
    assert 'value="4" checked' in page

    response = client.post(
        "/portal/evaluations/",
        {"enrollment_id": enrollment.pk, f"answer-{world.clear.pk}": "4", f"answer-{world.hard.pk}": "2"},
    )
    assert response.status_code == 302
    page = client.get("/portal/evaluations/").content.decode()
    assert "Thank you. Your evaluation was submitted." in page
    assert "data-done" in page
    assert EvaluationAnswer.objects.count() == 2

    # An enrollment that is not open for the student.
    other, _other_student = world.student()
    assert client.post("/portal/evaluations/", {"enrollment_id": other.pk}).status_code == 404
