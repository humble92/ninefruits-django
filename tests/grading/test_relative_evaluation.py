"""Relative evaluation and the grade caps, evaluation method requests, the fixed grade scale
(original ``tests/Feature/Grading/RelativeEvaluationTest.php``)."""

from __future__ import annotations

import re
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.urls import reverse

from ninefruits.audit.models import ActivityLog
from ninefruits.core.db import session_context
from ninefruits.grading.actions import ManageEvaluationMethodRequests, SaveGrades, SaveGradeScale
from ninefruits.grading.enums import EvaluationMethod, GradeStatus, RequestStatus
from ninefruits.grading.models import EvaluationMethodRequest, GradeScale
from ninefruits.grading.services import GradeDistributionCheck
from ninefruits.offering.models import SectionInstructor
from ninefruits.security.enums import Permission, ScopeType
from tests.factories.grading import GradeScaleFactory
from tests.factories.offering import SectionFactory
from tests.factories.organization import OrgUnitFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory

from .conftest import open_grade_entry, running_term, set_grading, teacher_of

pytestmark = pytest.mark.django_db

OVER = ["A+", "A0", "A+", "A0", "B+", "B0", "B+", "C+", "C0", "D0"]  # 4 A of 10
WITHIN = ["A+", "A0", "A+", "B+", "B+", "B0", "B+", "C+", "C0", "D0"]  # 3 A, 4 B of 10


@pytest.fixture
def world(korean_scale: Any) -> dict[str, Any]:
    set_grading(relative_grade_caps={"A": 30, "B": 40}, relative_cap_tolerance_percent=1, relative_minimum_students=10)
    term = running_term()
    open_grade_entry(term)
    section = SectionFactory(term=term, published=True, capacity=20, evaluation_method=EvaluationMethod.RELATIVE)
    teacher = teacher_of(section)
    unit_scope = {"permissions__scope_type": ScopeType.ORG_UNIT, "permissions__scope_id": section.org_unit_id}
    world = {
        "term": term,
        "section": section,
        "teacher": teacher,
        "registrar": UserFactory(
            permissions=[Permission.GRADES_VIEW, Permission.GRADES_MANAGE, Permission.GRADE_EXCEPTIONS_REVIEW]
        ),
        "reviewer": UserFactory(permissions=[Permission.GRADE_EXCEPTIONS_REVIEW], **unit_scope),
        # A reviewer of another department: not told about this section.
        "other_reviewer": UserFactory(
            permissions=[Permission.GRADE_EXCEPTIONS_REVIEW],
            permissions__scope_type=ScopeType.ORG_UNIT,
            permissions__scope_id=OrgUnitFactory().pk,
        ),
        "enrollments": [EnrollmentFactory(section=section) for _ in range(10)],
    }
    section.enrolled_count = 10
    section.save(update_fields=["enrolled_count"])
    return world


def grades_of(world: dict[str, Any], codes: list[str]) -> dict[int, dict[str, Any]]:
    return {e.pk: {"grade_code": code} for e, code in zip(world["enrollments"], codes, strict=True)}


def signed_in(user: Any) -> Client:
    client = Client()
    client.force_login(user)
    session_context().reset()
    return client


def test_checks_grade_groups_against_the_caps_with_tolerance_and_exempts_small_sections(world: dict[str, Any]) -> None:
    check = GradeDistributionCheck()

    # 4 of 10 A (40%) is over the 30% + 1 cap; 3 of 10 (30%) is not; 31% would still pass.
    assert not check.check(10, {"A": 4, "B": 4, "C": 2}).passes()
    assert check.check(10, {"A": 3, "B": 4, "C": 3}).passes()
    assert check.check(100, {"A": 31, "B": 40, "C": 29}).passes()
    assert len(check.check(100, {"A": 32, "B": 40, "C": 28}).violations) == 1
    # Under the minimum, or absolute evaluation: not checked.
    small = check.check(9, {"A": 9})
    assert not small.checked and small.passes()
    assert not check.check(50, {"A": 50}, relative=False).checked


def test_keeps_instructors_from_submitting_relative_grades_outside_the_caps(world: dict[str, Any]) -> None:
    section, teacher = world["section"], world["teacher"]
    SaveGrades().save(section, grades_of(world, OVER), teacher)

    with pytest.raises(ValidationError):
        SaveGrades().submit(section, teacher)
    world["enrollments"][0].refresh_from_db()
    assert world["enrollments"][0].grade_status == GradeStatus.DRAFT

    SaveGrades().save(section, grades_of(world, WITHIN), teacher)
    assert SaveGrades().submit(section, teacher) == 10
    section.refresh_from_db()
    assert section.grade_exception_at is None


def test_lets_staff_submit_outside_the_caps_only_as_a_recorded_exception_told_to_the_reviewers(
    world: dict[str, Any], mailoutbox: list[Any]
) -> None:
    section, registrar = world["section"], world["registrar"]
    SaveGrades().save(section, grades_of(world, OVER), registrar)

    with pytest.raises(ValidationError, match=re.escape("Submitting outside the grade caps needs a reason.")):
        SaveGrades().submit(section, registrar)

    SaveGrades().submit(section, registrar, "Honors seminar: the department approved the distribution")

    section.refresh_from_db()
    assert "Honors seminar" in section.grade_exception_reason
    assert section.grade_exception_by_id == registrar.pk
    world["enrollments"][0].refresh_from_db()
    assert world["enrollments"][0].grade_status == GradeStatus.SUBMITTED
    assert ActivityLog.objects.filter(event="grades.submitted_with_exception").count() == 1
    recipients = {address for message in mailoutbox for address in message.to}
    assert recipients == {world["reviewer"].email}

    page = signed_in(registrar).get(reverse("portal:grade_entry", args=[section.pk]))
    assert page.status_code == 200
    assert "Submitted as an exception." in page.content.decode()


def test_changes_the_evaluation_method_only_through_a_request_the_scheduling_staff_decide(
    world: dict[str, Any], mailoutbox: list[Any]
) -> None:
    section = SectionFactory(term=world["term"], published=True)
    instructor = SectionInstructor.objects.get(section=world["section"]).instructor
    SectionInstructor.objects.create(section=section, instructor=instructor, role="primary")
    enrollment = EnrollmentFactory(section=section)
    scheduler = UserFactory(
        permissions=[Permission.SECTIONS_MANAGE],
        permissions__scope_type=ScopeType.ORG_UNIT,
        permissions__scope_id=section.org_unit_id,
    )
    teacher = world["teacher"]
    requests = ManageEvaluationMethodRequests()

    assert section.evaluation_method == EvaluationMethod.ABSOLUTE
    with pytest.raises(PermissionDenied):
        requests.request(section, EvaluationMethod.RELATIVE, "Seminar", UserFactory())
    with pytest.raises(ValidationError):
        requests.request(section, EvaluationMethod.ABSOLUTE, "Same", teacher)

    SaveGrades().save(section, {enrollment.pk: {"score": "88"}}, teacher)
    request = requests.request(
        section, EvaluationMethod.RELATIVE, "Discussion seminar graded on participation", teacher
    )

    with pytest.raises(ValidationError):
        requests.request(section, EvaluationMethod.RELATIVE, "Again", teacher)
    with pytest.raises(PermissionDenied):
        requests.approve(request, UserFactory(permissions=[Permission.GRADES_MANAGE]))

    # Approval switches the method and clears the draft entered under the old one.
    assert requests.approve(request, scheduler, "Agreed") == 1
    section.refresh_from_db()
    enrollment.refresh_from_db()
    request.refresh_from_db()
    assert section.evaluation_method == EvaluationMethod.RELATIVE
    assert (enrollment.grade_status, enrollment.score) == (GradeStatus.NONE, None)
    assert request.status == RequestStatus.APPROVED
    assert [message.to for message in mailoutbox] == [[teacher.email]]

    # Not once grades are submitted.
    SaveGrades().save(section, {enrollment.pk: {"grade_code": "B0"}}, teacher)
    SaveGrades().submit(section, teacher)
    with pytest.raises(ValidationError, match="the evaluation method cannot change"):
        requests.request(section, EvaluationMethod.ABSOLUTE, "Back", teacher)


def test_lets_the_instructor_request_and_check_from_the_grade_entry_screen(world: dict[str, Any]) -> None:
    section = SectionFactory(term=world["term"], published=True)
    instructor = SectionInstructor.objects.get(section=world["section"]).instructor
    SectionInstructor.objects.create(section=section, instructor=instructor, role="primary")
    client = signed_in(world["teacher"])

    url = reverse("portal:grade_entry", args=[section.pk])
    page = client.post(url, {"action": "request_method", "method_reason": "Seminar"}, follow=True)
    content = page.content.decode()
    assert 'data-tone="success"' in content
    assert "Change to Relative evaluation requested and waiting for the scheduling staff." in content
    assert EvaluationMethodRequest.objects.filter(section=section).pending().exists()

    data: dict[str, Any] = {"action": "validate"}
    for enrollment, code in zip(world["enrollments"], OVER, strict=True):
        data[f"grade-{enrollment.pk}-code"] = code
    page = client.post(reverse("portal:grade_entry", args=[world["section"].pk]), data, follow=True)
    content = page.content.decode()
    assert 'data-tone="error"' in content
    assert "40" in content


def test_fixes_the_grade_scale_no_second_default_no_clearing_the_default(world: dict[str, Any]) -> None:
    other = GradeScaleFactory()

    with pytest.raises(ValidationError, match=re.escape("The grade scale is fixed at installation and cannot change.")):
        SaveGradeScale()(other, {"is_default": True})
    with pytest.raises(ValidationError):
        SaveGradeScale()(GradeScale.objects.get(is_default=True), {"is_default": False})
    assert SaveGradeScale()(other, {"name": {"en": "Renamed"}}).is_default is False
