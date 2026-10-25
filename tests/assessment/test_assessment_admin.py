"""Examination screens on the tiny demo (Phase 9 screens of the original
``tests/Feature/Admin/AdminPagesTest.php`` and the admin parts of ``AssessmentTest.php``): the demo
sessions, results and requirement; every examination page in English and Korean; publishing and
importing from the session list; recording an external result with evidence; requesting a
correction of a published result and approving it as someone else; the requirement kind
"passed examination" in the curriculum screen; the student's portal page."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from ninefruits.assessment.actions import RegisterForAssessment
from ninefruits.assessment.enums import AssessmentRegistrationStatus, CorrectionStatus, ResultSource
from ninefruits.assessment.models import (
    AssessmentRegistration,
    AssessmentResult,
    AssessmentResultCorrection,
    AssessmentSession,
    AssessmentType,
)
from ninefruits.curriculum.enums import RequirementKind
from ninefruits.curriculum.models import CurriculumRequirement, CurriculumRequirementSet
from ninefruits.security.enums import Permission
from ninefruits.security.models import User
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.demo.assessment import DemoAssessmentSeeder
from ninefruits.setup.seeders.demo.curriculum import DemoCurriculumSeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory

from .conftest import signed_in

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"


@pytest.fixture(autouse=True)
def demo(profile: None) -> Iterator[None]:
    with use_options(DemoOptions(size="tiny", seed=42)):
        for seeder in (
            DemoAccountSeeder,
            DemoReferenceSeeder,
            DemoPeopleSeeder,
            DemoCurriculumSeeder,
            DemoAssessmentSeeder,
        ):
            seeder()()
    yield


@pytest.fixture
def manager() -> User:
    return UserFactory(permissions=list(Permission))


@pytest.fixture
def registrar() -> User:
    return User.objects.get(email="registrar@demo.test")


def upcoming() -> AssessmentSession:
    return AssessmentSession.objects.get(held_date__gt=timezone.localdate())


def test_seeds_sessions_results_and_the_requirement_and_renders_the_examination_pages(manager: User) -> None:
    assert AssessmentSession.objects.count() == 4
    assert AssessmentSession.objects.filter(results_published_at__isnull=False).count() == 3
    assert AssessmentRegistration.objects.filter(session=upcoming()).count() > 0
    assert AssessmentResult.objects.filter(source=ResultSource.EXTERNAL, level__startswith="TOPIK").count() > 0
    assert AssessmentResult.objects.filter(is_passed=True).exists()
    assert CurriculumRequirement.objects.filter(kind=RequirementKind.ASSESSMENT_PASS).exists()

    english = AssessmentType.objects.get(code="ENG_COMP")
    past = AssessmentSession.objects.filter(results_published_at__isnull=False, assessment_type=english).first()
    assert past is not None
    registration = AssessmentRegistration.objects.filter(session=past, result__isnull=False).first()
    assert registration is not None
    requirement_set = CurriculumRequirementSet.objects.order_by("pk").first()
    assert requirement_set is not None
    client = signed_in(manager)
    pages = [
        "/admin/assessment/assessmentsession/",
        "/admin/assessment/assessmentsession/?published=no",
        f"/admin/assessment/assessmentsession/?type={english.pk}",
        "/admin/assessment/assessmentsession/add/",
        f"/admin/assessment/assessmentsession/{past.pk}/change/",
        f"/admin/assessment/assessmentsession/{past.pk}/change/?registrants=absent",
        f"/admin/assessment/assessmentsession/{upcoming().pk}/change/",
        f"/admin/assessment/assessmentsession/{upcoming().pk}/register-student/",
        f"/admin/assessment/assessmentsession/{upcoming().pk}/import/",
        f"/admin/assessment/assessmentsession/{upcoming().pk}/publish/",
        f"/admin/assessment/assessmentsession/{upcoming().pk}/import-results/",
        f"/admin/assessment/assessmentsession/{past.pk}/registrations/{registration.pk}/correct/",
        "/admin/assessment/assessmentresult/",
        "/admin/assessment/assessmentresult/?source=external&passed=yes",
        "/admin/assessment/assessmentresult/?q=TOPIK",
        "/admin/assessment/assessmentresult/record-external/",
        "/admin/assessment/assessmentresultcorrection/",
        "/admin/assessment/assessmentresultcorrection/?status=all",
        "/admin/assessment/assessmenttype/",
        "/admin/assessment/assessmenttype/add/",
        f"/admin/assessment/assessmenttype/{english.pk}/change/",
        f"/admin/curriculum/curriculumrequirementset/{requirement_set.pk}/change/",
    ]
    for page in pages:
        response = client.get(page)
        assert response.status_code == 200, page

    student = User.objects.get(email="student@demo.test")
    content = signed_in(student).get("/portal/assessments/").content.decode()
    assert "Open for registration" in content
    assert "Required by your curriculum" in content
    assert signed_in(student).get("/admin/assessment/assessmentresult/").status_code == 403


def test_renders_the_examination_pages_in_korean(manager: User) -> None:
    manager.locale = "ko"
    manager.save(update_fields=["locale"])
    client = signed_in(manager)
    assert "시험 회차" in client.get("/admin/assessment/assessmentsession/").content.decode()
    assert "시험 종류" in client.get("/admin/assessment/assessmenttype/").content.decode()
    assert "결과 정정 요청" in client.get("/admin/assessment/assessmentresultcorrection/").content.decode()
    student = User.objects.get(email="student@demo.test")
    student.locale = "ko"
    student.save(update_fields=["locale"])
    assert "접수 중인 회차" in signed_in(student).get("/portal/assessments/").content.decode()


def test_publishes_from_the_list_and_imports_results_from_the_session_page(registrar: User) -> None:
    session = upcoming()
    session.held_date = timezone.localdate()
    session.save(update_fields=["held_date"])
    RegisterForAssessment().register(session, StudentRecordFactory(), registrar, by_staff=True)
    registrations = list(AssessmentRegistration.objects.filter(session=session).select_related("student_record"))
    lines = ["student_number,listening,reading,writing,grammar,absent"]
    lines.append(f"{registrations[0].student_record.student_number},20,20,20,20,")
    lines.append(f"{registrations[1].student_record.student_number},,,,,Y")
    lines.append("NOPE,1,1,1,1,")
    upload = SimpleUploadedFile("results.csv", "\n".join(lines).encode(), content_type="text/csv")
    client = signed_in(registrar)

    response = client.post(f"/admin/assessment/assessmentsession/{session.pk}/import/", {"file": upload}, follow=True)
    assert response.status_code == 200
    content = response.content.decode()
    assert "1 recorded, 1 absent, 1 error(s)." in content
    assert "unknown student number [NOPE]" in content
    assert AssessmentResult.objects.filter(session=session).count() == 1
    assert AssessmentRegistration.objects.get(pk=registrations[1].pk).status == AssessmentRegistrationStatus.ABSENT

    response = client.post(f"/admin/assessment/assessmentsession/{session.pk}/publish-results/", {})
    assert response.status_code == 302
    session.refresh_from_db()
    assert session.results_published_at is not None
    # Published: the pass score is read only and the publish button refuses.
    assert client.get(f"/admin/assessment/assessmentsession/{session.pk}/publish-results/").status_code == 403


def test_changes_the_pass_score_from_the_session_form_and_judges_results_again(registrar: User) -> None:
    session = upcoming()
    session.held_date = timezone.localdate()
    session.save(update_fields=["held_date"])
    registration = AssessmentRegistration.objects.filter(session=session).first()
    assert registration is not None
    client = signed_in(registrar)
    url = f"/admin/assessment/assessmentsession/{session.pk}/registrations/{registration.pk}/result/"
    client.post(url, {"score_LISTENING": "14", "score_READING": "14", "score_WRITING": "14", "score_GRAMMAR": "13"})
    result = AssessmentResult.objects.get(registration=registration)
    assert result.is_passed is False

    data = {
        "held_date": session.held_date.isoformat(),
        "venue": session.venue,
        "capacity": session.capacity,
        "registration_opens_at_0": "",
        "registration_opens_at_1": "",
        "registration_closes_at_0": "",
        "registration_closes_at_1": "",
        "pass_score": "55",
        "pass_score_reason": "Hard paper",
    }
    response = client.post(f"/admin/assessment/assessmentsession/{session.pk}/change/", data, follow=True)
    assert response.status_code == 200
    assert "1 result(s) judged again: 1 now passed, 0 now failed." in response.content.decode()
    result.refresh_from_db()
    assert result.is_passed is True


def test_records_an_external_result_with_evidence_and_removes_it(registrar: User) -> None:
    record = AssessmentRegistration.objects.first().student_record  # type: ignore[union-attr]
    topik = AssessmentType.objects.get(code="TOPIK")
    client = signed_in(registrar)
    response = client.post(
        "/admin/assessment/assessmentresult/record-external/",
        {
            "student_number": record.student_number,
            "assessment_type": topik.pk,
            "taken_date": (timezone.localdate() - timedelta(days=10)).isoformat(),
            "passed": "1",
            "level": "TOPIK 4",
            "certificate_number": "T-42",
            "evidence": SimpleUploadedFile("topik.pdf", PDF, content_type="application/pdf"),
        },
    )
    assert response.status_code == 302
    result = AssessmentResult.objects.get(certificate_number="T-42")
    assert result.has_evidence()
    assert client.get(f"/assessment-results/{result.pk}/evidence/").status_code == 200
    assert "T-42" in client.get("/admin/assessment/assessmentresult/?q=" + record.student_number).content.decode()

    # A future date is refused by the form.
    response = client.post(
        "/admin/assessment/assessmentresult/record-external/",
        {
            "student_number": record.student_number,
            "assessment_type": topik.pk,
            "taken_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
            "passed": "1",
        },
    )
    assert response.status_code == 200
    assert "The date cannot be in the future." in response.content.decode()

    response = client.post(f"/admin/assessment/assessmentresult/{result.pk}/remove/", {"reason": "Wrong student"})
    assert response.status_code == 302
    assert not AssessmentResult.objects.filter(pk=result.pk).exists()


def test_requests_a_correction_of_a_published_result_and_approves_it_as_someone_else(
    registrar: User, manager: User
) -> None:
    result = (
        AssessmentResult.objects.filter(
            session__results_published_at__isnull=False, session__assessment_type__code="ENG_COMP"
        )
        .select_related("registration")
        .first()
    )
    assert result is not None
    url = f"/admin/assessment/assessmentsession/{result.session_id}/registrations/{result.registration_id}/correct/"
    response = signed_in(registrar).post(
        url,
        {
            "score_LISTENING": "25",
            "score_READING": "25",
            "score_WRITING": "25",
            "score_GRAMMAR": "25",
            "reason": "Marking error",
        },
    )
    assert response.status_code == 302
    correction = AssessmentResultCorrection.objects.get()
    assert correction.status == CorrectionStatus.PENDING
    # The requester cannot decide their own request.
    assert (
        signed_in(registrar).get(f"/admin/assessment/assessmentresultcorrection/{correction.pk}/approve/").status_code
        == 403
    )

    response = signed_in(manager).post(
        f"/admin/assessment/assessmentresultcorrection/{correction.pk}/approve/", {"note": "Checked"}
    )
    assert response.status_code == 302
    correction.refresh_from_db()
    result.refresh_from_db()
    assert correction.status == CorrectionStatus.APPROVED
    assert str(result.total_score) == "100.0"
    assert result.is_passed is True


def test_adds_a_passed_examination_requirement_in_the_curriculum_screen(manager: User) -> None:
    requirement_set = CurriculumRequirementSet.objects.order_by("pk").first()
    assert requirement_set is not None
    english = AssessmentType.objects.get(code="ENG_COMP")
    content = signed_in(manager).get(f"/admin/curriculum/curriculumrequirementset/{requirement_set.pk}/change/").content
    assert english.code.encode() in content or str(english.name).encode() in content
    requirement = CurriculumRequirement.objects.filter(
        requirement_set=requirement_set, kind=RequirementKind.ASSESSMENT_PASS
    ).first()
    assert requirement is not None
    assert requirement.assessment_type == english
    assert english.requirements.filter(pk=requirement.pk).exists()


def test_registers_and_cancels_in_the_portal_with_htmx(manager: User) -> None:
    session = upcoming()
    student = User.objects.get(email="student@demo.test")
    AssessmentRegistration.objects.filter(session=session, student_record__person_id=student.person_id).delete()
    client = signed_in(student)
    response = client.post(
        "/portal/assessments/", {"action": "register", "session_id": session.pk}, HTTP_HX_REQUEST="true", follow=True
    )
    assert "You are registered." in response.content.decode()
    registration = AssessmentRegistration.objects.get(session=session, student_record__person_id=student.person_id)
    response = client.post(
        "/portal/assessments/", {"action": "cancel", "registration_id": registration.pk}, follow=True
    )
    assert "Your registration is cancelled." in response.content.decode()
    registration.refresh_from_db()
    assert registration.status == AssessmentRegistrationStatus.CANCELLED
    # Someone else's registration is not found.
    other = AssessmentRegistration.objects.exclude(student_record__person_id=student.person_id).first()
    assert other is not None
    assert client.post("/portal/assessments/", {"action": "cancel", "registration_id": other.pk}).status_code == 404
