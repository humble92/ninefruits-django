"""Grading screens on the tiny demo (original ``tests/Feature/Admin/GradingAdminTest.php`` and the
Phase 6 datasets of ``AdminPagesTest.php``): demo grades, term records and a change request;
every grading page; finalizing a submitted section and approving the pending change request as
someone else; previewing a term close; grade entry in the portal and the student's grades; a
hold that blocks grades."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from django.test import Client

from ninefruits.core.db import session_context
from ninefruits.grading.enums import EvaluationMethod, GradeChangeStatus, GradeStatus
from ninefruits.grading.models import GradeChangeRequest, TermRecord
from ninefruits.offering.models import Section
from ninefruits.person.models import StudentRecord
from ninefruits.registration.actions import ManageHolds
from ninefruits.registration.enums import EnrollmentStatus, HoldType
from ninefruits.registration.models import Enrollment
from ninefruits.security.enums import Permission
from ninefruits.security.models import User
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.demo.curriculum import DemoCurriculumSeeder
from ninefruits.setup.seeders.demo.grading import DemoGradeHistorySeeder, DemoGradingSeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from ninefruits.setup.seeders.demo.registration import DemoRegistrationSeeder
from ninefruits.term.enums import TermStatus
from ninefruits.term.models import Term
from tests.factories.security import UserFactory

from .conftest import set_grading

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def demo(essential_data: None) -> Iterator[None]:
    # Honors thresholds low enough that the small random demo always produces honors students.
    set_grading(honors_min_gpa=3.0, honors_min_credits=3.0)
    with use_options(DemoOptions(size="tiny", seed=42)):
        for seeder in (
            DemoAccountSeeder,
            DemoReferenceSeeder,
            DemoPeopleSeeder,
            DemoCurriculumSeeder,
            DemoGradeHistorySeeder,
            DemoRegistrationSeeder,
            DemoGradingSeeder,
        ):
            seeder()()
    yield


@pytest.fixture
def manager() -> User:
    return UserFactory(permissions=list(Permission))


@pytest.fixture
def registrar() -> User:
    return User.objects.get(email="registrar@demo.test")


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    session_context().reset()
    return client


def test_seeds_grades_term_records_and_a_change_request_and_renders_the_grading_pages(manager: User) -> None:
    assert Enrollment.objects.filter(grade_status=GradeStatus.FINALIZED).exists()
    assert Enrollment.objects.filter(grade_status=GradeStatus.SUBMITTED).exists()
    assert TermRecord.objects.filter(closed_at__isnull=False, academic_standing="warning").exists()
    assert TermRecord.objects.filter(is_honors=True).exists()
    assert GradeChangeRequest.objects.filter(status=GradeChangeStatus.PENDING).count() == 1

    section = Section.objects.filter(enrollments__isnull=False).order_by("pk").first()
    record = TermRecord.objects.order_by("pk").first()
    change = GradeChangeRequest.objects.get()
    client = signed_in(manager)
    pages = [
        "/admin/grading/sectiongrade/",
        "/admin/grading/sectiongrade/?ready=yes",
        "/admin/grading/sectiongrade/?exception=yes&term=all",
        f"/admin/grading/sectiongrade/{section.pk}/finalize/",
        f"/admin/grading/sectiongrade/{section.pk}/return/",
        "/admin/grading/gradechangerequest/",
        "/admin/grading/gradechangerequest/?status=all",
        f"/admin/grading/gradechangerequest/{change.pk}/approve/",
        f"/admin/grading/gradechangerequest/{change.pk}/reject/",
        "/admin/grading/evaluationmethodrequest/",
        "/admin/grading/termrecord/",
        "/admin/grading/termrecord/?honors=yes&academic_standing=all",
        "/admin/grading/termrecord/close-term/",
        "/admin/grading/termrecord/recalculate/",
        "/admin/settings/grading/",
        f"/portal/sections/{section.pk}/grades/",
        f"/student-records/{record.student_record_id}/transcript/",
        f"/admin/person/studentrecord/{record.student_record_id}/change/",
    ]
    for page in pages:
        response = client.get(page)
        assert response.status_code == 200, page

    student = User.objects.get(email="student@demo.test")
    client = signed_in(student)
    assert client.get("/portal/grades/").status_code == 200
    assert client.get("/portal/grades/transcript/").status_code == 200
    assert client.get(f"/student-records/{record.student_record_id}/transcript/").status_code == 403


def test_renders_the_grading_pages_in_korean(manager: User) -> None:
    manager.locale = "ko"
    manager.save(update_fields=["locale"])
    content = signed_in(manager).get("/admin/grading/termrecord/").content.decode()
    assert "학기 기록" in content


def test_finalizes_a_submitted_section_and_approves_the_pending_change_request_as_someone_else(
    registrar: User,
) -> None:
    section = Section.objects.filter(enrollments__grade_status=GradeStatus.SUBMITTED).distinct().get()
    client = signed_in(registrar)

    response = client.post(f"/admin/grading/sectiongrade/{section.pk}/finalize/", {})
    assert response.status_code == 302
    assert section.enrollments.filter(grade_status=GradeStatus.FINALIZED).exists()
    assert not section.enrollments.filter(grade_status=GradeStatus.SUBMITTED).exists()

    change = GradeChangeRequest.objects.pending().get()
    response = client.post(f"/admin/grading/gradechangerequest/{change.pk}/approve/", {"note": "Checked"})
    assert response.status_code == 302
    change.refresh_from_db()
    assert change.status == GradeChangeStatus.APPROVED
    assert Enrollment.objects.get(pk=change.enrollment_id).grade_code == change.to_grade_code


def test_previews_a_term_close_and_refuses_an_unfinished_term(registrar: User) -> None:
    current = Term.objects.filter(status=TermStatus.PUBLISHED).order_by("start_date").first()
    client = signed_in(registrar)

    response = client.post("/admin/grading/termrecord/close-term/", {"term_id": current.pk}, follow=True)
    assert response.status_code == 200
    assert "Cannot close yet" in response.content.decode()
    current.refresh_from_db()
    assert current.status == TermStatus.PUBLISHED


def test_lets_the_instructor_enter_grades_in_the_portal_and_the_student_see_final_ones() -> None:
    instructor = User.objects.get(email="instructor@demo.test")
    section = (
        Section.objects.taught_by(instructor.person_id)
        .filter(enrolled_count__gt=0, term__status=TermStatus.PUBLISHED)
        .order_by("pk")
        .first()
    )
    enrollment = section.enrollments.filter(status=EnrollmentStatus.ENROLLED).order_by("pk").first()
    section.evaluation_method = EvaluationMethod.ABSOLUTE
    section.save(update_fields=["evaluation_method"])
    client = signed_in(instructor)
    url = f"/portal/sections/{section.pk}/grades/"

    page = client.get(url).content.decode()
    assert "Absolute evaluation" in page
    # Absolute evaluation: the score shows its grade right away.
    preview = client.get(url, {"preview": enrollment.pk, f"grade-{enrollment.pk}-score": "86"}, HTTP_HX_REQUEST="true")
    assert ">B+</span>" in preview.content.decode()

    response = client.post(url, {"action": "save", f"grade-{enrollment.pk}-score": "86"}, follow=True)
    assert 'data-tone="success"' in response.content.decode()
    enrollment.refresh_from_db()
    assert (enrollment.grade_code, str(enrollment.score), enrollment.grade_status) == ("B+", "86.00", GradeStatus.DRAFT)

    # Drafts stay hidden from the student; final grades show.
    record = enrollment.student_record
    student = getattr(record.person, "user", None) or UserFactory(person=record.person)
    page = signed_in(student).get("/portal/grades/").content.decode()
    assert str(section.term.name) not in page
    final = (
        Enrollment.objects.filter(student_record=record, grade_status=GradeStatus.FINALIZED)
        .select_related("course")
        .first()
    )
    if final is not None:
        assert final.course.code in page


def test_hides_grades_from_a_student_with_a_hold_that_blocks_them(registrar: User) -> None:
    record = StudentRecord.objects.filter(enrollments__grade_status=GradeStatus.FINALIZED).order_by("pk").first()
    student = getattr(record.person, "user", None) or UserFactory(person=record.person)
    ManageHolds().place(
        record, HoldType.ACADEMIC, "Integrity investigation", registrar, blocks_registration=False, blocks_grades=True
    )
    client = signed_in(student)

    page = client.get("/portal/grades/").content.decode()
    assert "Your grades are not available: you have a hold (Academic)." in page
    assert client.get("/portal/grades/transcript/").status_code == 403
