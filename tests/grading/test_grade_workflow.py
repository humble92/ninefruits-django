"""Grade entry, finalizing, returning and grade changes (original
``tests/Feature/Grading/GradeWorkflowTest.php``). The actions run with the acting user's
database context (row level security applies, like a real request)."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from ninefruits.curriculum.enums import GradingBasis
from ninefruits.grading.actions import FinalizeGrades, ManageGradeChanges, SaveGrades
from ninefruits.grading.enums import EvaluationMethod, GradeChangeStatus, GradeStatus
from ninefruits.grading.events import GradesFinalized
from ninefruits.grading.models import TermRecord
from ninefruits.offering.actions import UpdateSection
from ninefruits.registration.enums import EnrollmentStatus
from ninefruits.security.enums import Permission
from tests.factories.offering import SectionFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory

from .conftest import now, open_grade_entry, running_term, set_grading, teacher_of

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(korean_scale: Any, as_user: Any) -> dict[str, Any]:
    term = running_term()
    window = open_grade_entry(term)
    # Relative evaluation (grades only) unless a test switches to absolute (scores).
    section = SectionFactory(term=term, published=True, capacity=10, evaluation_method=EvaluationMethod.RELATIVE)
    teacher = teacher_of(section)
    # grades.view as well: under row level security, staff read enrollments through it (every
    # role with grades.manage has it).
    registrar = UserFactory(
        permissions=[Permission.GRADES_VIEW, Permission.GRADES_MANAGE, Permission.GRADE_CHANGES_APPROVE]
    )
    clerk = UserFactory(
        permissions=[Permission.GRADES_VIEW, Permission.GRADE_CHANGES_REQUEST, Permission.GRADE_CHANGES_APPROVE]
    )
    enrollments = [EnrollmentFactory(section=section) for _ in range(3)]
    section.enrolled_count = 3
    section.save(update_fields=["enrolled_count"])
    return {
        "term": term,
        "window": window,
        "section": section,
        "teacher": teacher,
        "registrar": registrar,
        "clerk": clerk,
        "enrollments": enrollments,
        "as_user": as_user,
    }


def grades(world: dict[str, Any], codes: list[str | None]) -> dict[int, dict[str, Any]]:
    return {e.pk: {"grade_code": code} for e, code in zip(world["enrollments"], codes, strict=True)}


def scores(world: dict[str, Any], values: list[str]) -> dict[int, dict[str, Any]]:
    return {e.pk: {"score": value} for e, value in zip(world["enrollments"], values, strict=True)}


def act(world: dict[str, Any], user: Any, call: Any) -> Any:
    with world["as_user"](user):
        return call()


def make_absolute(world: dict[str, Any]) -> None:
    world["section"].evaluation_method = EvaluationMethod.ABSOLUTE
    world["section"].save(update_fields=["evaluation_method"])


def finalize_all(world: dict[str, Any], entered: dict[int, dict[str, Any]]) -> None:
    section, teacher, registrar = world["section"], world["teacher"], world["registrar"]
    act(world, teacher, lambda: SaveGrades().save(section, entered, teacher))
    act(world, teacher, lambda: SaveGrades().submit(section, teacher))
    act(world, registrar, lambda: FinalizeGrades().finalize(section, registrar))


def test_lets_the_instructor_save_drafts_and_submit_then_locks_the_grades_for_them(world: dict[str, Any]) -> None:
    section, teacher, enrollments = world["section"], world["teacher"], world["enrollments"]

    assert act(world, teacher, lambda: SaveGrades().save(section, grades(world, ["A+", "B0", None]), teacher)) == 2
    with pytest.raises(ValidationError):
        act(world, teacher, lambda: SaveGrades().submit(section, teacher))

    # Relative evaluation: grades only.
    with pytest.raises(ValidationError):
        act(world, teacher, lambda: SaveGrades().save(section, {enrollments[2].pk: {"score": "91.5"}}, teacher))
    act(world, teacher, lambda: SaveGrades().save(section, {enrollments[2].pk: {"grade_code": "A0"}}, teacher))
    enrollments[2].refresh_from_db()
    assert enrollments[2].grade_code == "A0"
    assert enrollments[2].score is None
    assert str(enrollments[2].grade_points) == "4.00"
    assert enrollments[2].grade_status == GradeStatus.DRAFT

    assert act(world, teacher, lambda: SaveGrades().submit(section, teacher)) == 3
    with pytest.raises(ValidationError):
        act(world, teacher, lambda: SaveGrades().save(section, grades(world, ["F", "F", "F"]), teacher))
    enrollments[0].refresh_from_db()
    assert enrollments[0].grade_code == "A+"


def test_turns_scores_into_grades_for_absolute_evaluation(world: dict[str, Any]) -> None:
    make_absolute(world)
    section, teacher, enrollments = world["section"], world["teacher"], world["enrollments"]

    # Absolute evaluation takes scores; a letter grade with GPA value cannot be chosen.
    with pytest.raises(ValidationError):
        act(world, teacher, lambda: SaveGrades().save(section, {enrollments[0].pk: {"grade_code": "A0"}}, teacher))

    act(
        world,
        teacher,
        lambda: SaveGrades().save(
            section, {enrollments[0].pk: {"score": "91.5"}, enrollments[1].pk: {"score": "97"}}, teacher
        ),
    )
    first, second = (e.__class__.objects.get(pk=e.pk) for e in enrollments[:2])
    assert (first.grade_code, str(first.grade_points), str(first.score)) == ("A0", "4.00", "91.50")
    assert (second.grade_code, str(second.grade_points)) == ("A+", "4.50")


def test_lowers_an_absolute_retake_above_the_cap_to_the_cap_and_keeps_the_score(world: dict[str, Any]) -> None:
    make_absolute(world)
    retake = world["enrollments"][0]
    retake.is_retake = True
    retake.save(update_fields=["is_retake"])
    set_grading(retake_max_grade="B+")

    teacher = world["teacher"]
    act(world, teacher, lambda: SaveGrades().save(world["section"], {retake.pk: {"score": "98"}}, teacher))
    retake.refresh_from_db()
    assert (retake.grade_code, str(retake.score)) == ("B+", "98.00")


def test_changes_an_absolute_grade_by_a_new_score_and_refuses_a_bare_grade(world: dict[str, Any]) -> None:
    make_absolute(world)
    finalize_all(world, scores(world, ["81", "81", "81"]))
    enrollment = (
        world["enrollments"][0]
        .__class__.objects.select_related("section", "version")
        .get(pk=world["enrollments"][0].pk)
    )
    teacher, registrar = world["teacher"], world["registrar"]

    with pytest.raises(ValidationError):
        act(world, teacher, lambda: ManageGradeChanges().request(enrollment, "A0", "Regrade", teacher))

    change = act(
        world, teacher, lambda: ManageGradeChanges().request(enrollment, None, "Exam re-marked", teacher, "92")
    )
    assert (change.to_grade_code, str(change.to_score)) == ("A0", "92.00")

    act(world, registrar, lambda: ManageGradeChanges().approve(change, registrar))
    enrollment.refresh_from_db()
    assert (enrollment.grade_code, str(enrollment.score)) == ("A0", "92.00")


def test_keeps_the_retake_cap_through_gpa_and_grade_changes_and_only_for_retakes(world: dict[str, Any]) -> None:
    make_absolute(world)
    retake, first, other = world["enrollments"]
    retake.is_retake = True
    retake.save(update_fields=["is_retake"])
    set_grading(retake_max_grade="B+")
    section, teacher, registrar = world["section"], world["teacher"], world["registrar"]

    act(
        world,
        teacher,
        lambda: SaveGrades().save(
            section, {retake.pk: {"score": "98"}, first.pk: {"score": "98"}, other.pk: {"score": "70"}}, teacher
        ),
    )
    retake.refresh_from_db()
    first.refresh_from_db()
    # Same score: the retake is capped, the first attempt is not.
    assert (retake.grade_code, str(retake.grade_points), str(retake.score)) == ("B+", "3.50", "98.00")
    assert (first.grade_code, str(first.grade_points)) == ("A+", "4.50")

    act(world, teacher, lambda: SaveGrades().submit(section, teacher))
    act(world, registrar, lambda: FinalizeGrades().finalize(section, registrar))

    # The GPA uses the capped grade points, never the score.
    assert str(TermRecord.objects.get(student_record_id=retake.student_record_id).term_gpa) == "3.50"
    assert str(TermRecord.objects.get(student_record_id=first.student_record_id).term_gpa) == "4.50"

    # A changed score on the retake goes through the cap again.
    retake = retake.__class__.objects.select_related("section", "version").get(pk=retake.pk)
    change = act(world, teacher, lambda: ManageGradeChanges().request(retake, None, "Exam re-marked", teacher, "100"))
    assert change.to_grade_code == "B+"
    act(world, registrar, lambda: ManageGradeChanges().approve(change, registrar))

    retake.refresh_from_db()
    assert (retake.grade_code, str(retake.score)) == ("B+", "100.00")
    assert str(TermRecord.objects.get(student_record_id=retake.student_record_id).term_gpa) == "3.50"


def test_does_not_change_the_evaluation_method_once_grades_are_entered(world: dict[str, Any]) -> None:
    section, teacher = world["section"], world["teacher"]
    act(world, teacher, lambda: SaveGrades().save(section, {world["enrollments"][0].pk: {"grade_code": "B0"}}, teacher))
    planner = UserFactory(permissions=[Permission.SECTIONS_MANAGE])

    with pytest.raises(ValidationError, match="the evaluation method cannot change"):
        UpdateSection()(section, {"evaluation_method": "absolute"}, planner)


def test_refuses_entry_outside_the_window_and_by_other_instructors_but_not_by_grade_staff(
    world: dict[str, Any],
) -> None:
    window = world["window"]
    window.closes_at = now() - timedelta(minutes=1)
    window.save(update_fields=["closes_at"])
    section, teacher, registrar = world["section"], world["teacher"], world["registrar"]
    entered = grades(world, ["A0", "A0", "A0"])

    with pytest.raises(ValidationError, match=re.escape("Grade entry is not open for this section.")):
        SaveGrades().save(section, entered, teacher)
    with pytest.raises(PermissionDenied):
        SaveGrades().save(section, entered, UserFactory())
    assert act(world, registrar, lambda: SaveGrades().save(section, entered, registrar)) == 3


def test_caps_retakes_at_the_configured_grade_and_offers_only_p_np_for_pass_fail_courses(
    world: dict[str, Any],
) -> None:
    section, teacher, enrollments = world["section"], world["teacher"], world["enrollments"]
    retake = enrollments[1]
    retake.is_retake = True
    retake.save(update_fields=["is_retake"])
    set_grading(retake_max_grade="A0")

    with pytest.raises(ValidationError):
        SaveGrades().save(section, {retake.pk: {"grade_code": "A+"}}, teacher)
    saved = SaveGrades().save(
        section, {retake.pk: {"grade_code": "A0"}, enrollments[0].pk: {"grade_code": "A+"}}, teacher
    )
    assert saved == 2

    section.version.grading_basis = GradingBasis.PASS_FAIL
    section.version.save(update_fields=["grading_basis"])

    with pytest.raises(ValidationError):
        SaveGrades().save(section, {enrollments[2].pk: {"grade_code": "A0"}}, teacher)
    assert SaveGrades().save(section, {enrollments[2].pk: {"grade_code": "P"}}, teacher) == 1
    enrollments[2].refresh_from_db()
    assert enrollments[2].counts_in_gpa is False
    assert enrollments[2].is_passed is True


def test_finalizes_submitted_grades_into_completed_enrollments_and_term_records(world: dict[str, Any]) -> None:
    from ninefruits.core.events import listen

    seen: list[Any] = []
    listen(GradesFinalized)(seen.append)
    section, teacher, registrar = world["section"], world["teacher"], world["registrar"]
    act(world, teacher, lambda: SaveGrades().save(section, grades(world, ["A+", "B0", "F"]), teacher))

    with pytest.raises(ValidationError):
        act(world, registrar, lambda: FinalizeGrades().finalize(section, registrar))

    act(world, teacher, lambda: SaveGrades().submit(section, teacher))
    with pytest.raises(PermissionDenied):
        FinalizeGrades().finalize(section, teacher)
    assert act(world, registrar, lambda: FinalizeGrades().finalize(section, registrar)) == 3

    failed = world["enrollments"][2]
    failed.refresh_from_db()
    assert failed.status == EnrollmentStatus.COMPLETED
    assert failed.grade_status == GradeStatus.FINALIZED
    assert failed.is_passed is False
    record = TermRecord.objects.get(student_record_id=failed.student_record_id)
    assert str(record.term_gpa) == "0.00"
    assert str(record.earned_credits) == "0.0"
    assert [event.section.pk for event in seen] == [section.pk]


def test_returns_submitted_grades_to_the_instructor_with_a_reason(world: dict[str, Any], mailoutbox: list[Any]) -> None:
    section, teacher, registrar = world["section"], world["teacher"], world["registrar"]
    act(world, teacher, lambda: SaveGrades().save(section, grades(world, ["A+", "B0", "C0"]), teacher))
    act(world, teacher, lambda: SaveGrades().submit(section, teacher))

    assert (
        act(world, registrar, lambda: FinalizeGrades().return_grades(section, registrar, "C0 looks like a typo")) == 3
    )
    world["enrollments"][2].refresh_from_db()
    assert world["enrollments"][2].grade_status == GradeStatus.DRAFT
    assert [message.to for message in mailoutbox] == [[teacher.email]]
    assert "C0 looks like a typo" in mailoutbox[0].body


def test_changes_a_finalized_grade_only_through_a_request_decided_by_someone_else(world: dict[str, Any]) -> None:
    finalize_all(world, grades(world, ["B0", "B0", "B0"]))
    enrollment = (
        world["enrollments"][0]
        .__class__.objects.select_related("section", "version")
        .get(pk=world["enrollments"][0].pk)
    )
    teacher, registrar, clerk = world["teacher"], world["registrar"], world["clerk"]
    changes = ManageGradeChanges()

    with pytest.raises(PermissionDenied):
        changes.request(enrollment, "A0", "Regrade", UserFactory())

    change = act(world, teacher, lambda: changes.request(enrollment, "A0", "Missing assignment added", teacher))

    with pytest.raises(ValidationError):
        act(world, teacher, lambda: changes.request(enrollment, "A+", "Again", teacher))
    with pytest.raises(ValidationError):
        changes.approve(change, teacher)

    act(world, registrar, lambda: changes.approve(change, registrar, "Checked the submission"))
    change.refresh_from_db()
    enrollment.refresh_from_db()
    assert change.status == GradeChangeStatus.APPROVED
    assert change.applied_at is not None
    assert (enrollment.grade_code, str(enrollment.grade_points)) == ("A0", "4.00")
    assert str(TermRecord.objects.get(student_record_id=enrollment.student_record_id).term_gpa) == "4.00"

    # Staff requests follow the same rule: the clerk cannot approve their own.
    own = act(world, clerk, lambda: changes.request(enrollment, "B+", "Late penalty", clerk))
    with pytest.raises(ValidationError, match=re.escape("You cannot decide your own request.")):
        changes.approve(own, clerk)
    act(world, registrar, lambda: changes.reject(own, registrar, "The penalty does not apply"))
    own.refresh_from_db()
    enrollment.refresh_from_db()
    assert own.status == GradeChangeStatus.REJECTED
    assert enrollment.grade_code == "A0"


def test_records_a_staff_change_of_a_submitted_grade_in_the_audit(world: dict[str, Any]) -> None:
    from ninefruits.audit.models import ActivityLog

    section, teacher, registrar = world["section"], world["teacher"], world["registrar"]
    act(world, teacher, lambda: SaveGrades().save(section, grades(world, ["A+", "B0", "C0"]), teacher))
    act(world, teacher, lambda: SaveGrades().submit(section, teacher))

    first = world["enrollments"][0]
    act(world, registrar, lambda: SaveGrades().save(section, {first.pk: {"grade_code": "A0"}}, registrar))
    first.refresh_from_db()
    assert (first.grade_code, first.grade_status) == ("A0", GradeStatus.SUBMITTED)
    entry = ActivityLog.objects.get(event="grades.submitted_changed")
    assert entry.properties["from"] == {"grade_code": "A+", "score": None}
    assert entry.properties["to"] == {"grade_code": "A0", "score": None}


def test_requests_and_cancels_a_change_from_the_grade_entry_screen(world: dict[str, Any]) -> None:
    from django.test import Client

    from ninefruits.core.db import session_context
    from ninefruits.grading.models import GradeChangeRequest

    finalize_all(world, grades(world, ["B0", "B0", "B0"]))
    enrollment = world["enrollments"][0]
    client = Client()
    client.force_login(world["teacher"])
    session_context().reset()
    url = f"/portal/sections/{world['section'].pk}/grades/"

    form = client.get(url, {"change": enrollment.pk}).content.decode()
    assert "data-change-form" in form
    # A missing reason keeps the form open with the error.
    page = client.post(url, {"action": "request_change", "enrollment_id": enrollment.pk, "change_grade": "A0"})
    assert 'data-tone="error"' in page.content.decode()
    assert "data-change-form" in page.content.decode()

    data = {
        "action": "request_change",
        "enrollment_id": enrollment.pk,
        "change_grade": "A0",
        "change_reason": "Re-marked",
    }
    page = client.post(url, data, follow=True).content.decode()
    assert "Grade change requested." in page
    change = GradeChangeRequest.objects.get(enrollment=enrollment)
    assert change.status == GradeChangeStatus.PENDING

    client.post(url, {"action": f"cancel_change:{change.pk}"}, follow=True)
    change.refresh_from_db()
    assert change.status == GradeChangeStatus.CANCELLED
