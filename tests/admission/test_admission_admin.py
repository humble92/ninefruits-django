"""Original tests/Feature/Admin/AdmissionAdminTest.php (and admission pages of AdminPagesTest.php),
plus the admin decision actions of ViewApplication."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.utils.html import escape

from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import DOCUMENT_TYPE_LOOKUP, AdmissionCycle, Application
from ninefruits.institution.models import LookupValue
from ninefruits.organization.models import Program
from ninefruits.person.models import StudentRecord
from ninefruits.security.enums import Permission
from ninefruits.security.models import User
from ninefruits.setup.seeders.demo.admission import DemoAdmissionSeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("demo_admissions")]


@pytest.fixture
def demo_admissions(admission_reference: None, mfa_disabled: None) -> None:
    DemoReferenceSeeder()()
    DemoPeopleSeeder()()
    DemoAdmissionSeeder()()


@pytest.fixture
def manager() -> User:
    return UserFactory(permissions=list(Permission))


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def test_renders_the_admission_pages(manager: User) -> None:
    cycle = AdmissionCycle.objects.first()
    application = Application.objects.exclude(status=ApplicationStatus.DRAFT).first()
    assert cycle is not None and application is not None
    pages = [
        "/admin/admission/admissioncycle/",
        "/admin/admission/admissioncycle/add/",
        f"/admin/admission/admissioncycle/{cycle.pk}/change/",
        "/admin/admission/application/",
        "/admin/admission/application/?q=DEMO",
        f"/admin/admission/application/{application.pk}/change/",
        "/admin/settings/admissions/",
    ]
    client = signed_in(manager)
    for url in pages:
        response = client.get(url)
        assert response.status_code == 200, url


def test_renders_the_admission_pages_in_korean_and_chinese(manager: User) -> None:
    for locale, text in (("ko", "모집 회차"), ("zh-hans", "招生批次")):
        manager.locale = locale
        manager.save()
        response = signed_in(manager).get("/admin/admission/admissioncycle/")
        assert response.status_code == 200
        assert text in response.content.decode()


def test_creates_a_cycle_with_programs_and_documents(manager: User) -> None:
    program = Program.objects.effective_on().first()
    document = LookupValue.objects.of_type(DOCUMENT_TYPE_LOOKUP).first()
    assert program is not None and document is not None

    response = signed_in(manager).post(
        "/admin/admission/admissioncycle/add/",
        {
            "code": "2028-SPRING",
            "name__en": "2028 spring admission",
            "name__ko": "2028학년도 1학기 모집",
            "opens_at_0": "2028-01-02",
            "opens_at_1": "09:00",
            "is_published": "on",
            "programs-TOTAL_FORMS": "1",
            "programs-INITIAL_FORMS": "0",
            "programs-0-program": str(program.pk),
            "programs-0-capacity": "40",
            "document_types-TOTAL_FORMS": "1",
            "document_types-INITIAL_FORMS": "0",
            "document_types-0-document_type": str(document.pk),
            "document_types-0-is_required": "on",
        },
    )
    assert response.status_code == 302, response.content.decode()[:3000]

    cycle = AdmissionCycle.objects.get(code="2028-SPRING")
    assert cycle.is_rolling()
    assert cycle.programs.get().capacity == 40
    assert cycle.document_types.count() == 1


def test_lists_submitted_applications_but_never_drafts_and_releases_decisions_in_bulk(manager: User) -> None:
    draft = Application.objects.filter(status=ApplicationStatus.DRAFT).first()
    admitted = list(
        Application.objects.filter(status=ApplicationStatus.ADMITTED, decision_released_at__isnull=True).values_list(
            "pk", flat=True
        )
    )
    assert draft is not None and admitted
    client = signed_in(manager)

    listing = client.get("/admin/admission/application/").content.decode()
    assert f"/admin/admission/application/{draft.pk}/change/" not in listing
    assert client.get(f"/admin/admission/application/{draft.pk}/change/").status_code == 302

    response = client.post(
        "/admin/admission/application/",
        {"action": "release_selected", "_selected_action": [str(pk) for pk in admitted]},
    )
    assert response.status_code == 302
    assert not Application.objects.filter(pk__in=admitted, decision_released_at__isnull=True).exists()


def test_releases_a_cycle_from_the_cycle_list(manager: User) -> None:
    cycle = AdmissionCycle.objects.get(code__endswith="-REG")
    assert Application.objects.filter(
        admission_cycle=cycle, status=ApplicationStatus.ADMITTED, decision_released_at__isnull=True
    ).exists()

    response = signed_in(manager).post(
        f"/admin/admission/admissioncycle/{cycle.pk}/release-decisions/", {"_form_submitted": "1"}
    )
    assert response.status_code == 302
    assert not Application.objects.filter(
        admission_cycle=cycle, status__in=["admitted", "rejected"], decision_released_at__isnull=True
    ).exists()


def test_decides_and_matriculates_from_the_application_page(manager: User) -> None:
    client = signed_in(manager)
    application = Application.objects.filter(status=ApplicationStatus.SUBMITTED).first()
    assert application is not None
    base = f"/admin/admission/application/{application.pk}"

    assert client.post(f"{base}/start-review/", {"_form_submitted": "1"}).status_code == 302
    application.refresh_from_db()
    assert application.status == ApplicationStatus.UNDER_REVIEW

    # Rejecting needs a note; the dialog is shown again without one.
    assert client.post(f"{base}/reject/", {"_form_submitted": "1"}).status_code == 200
    assert client.post(f"{base}/admit/", {"_form_submitted": "1", "note": "Good"}).status_code == 302
    assert client.post(f"{base}/release/", {"_form_submitted": "1"}).status_code == 302
    application.refresh_from_db()
    assert application.applicant_status() == ApplicationStatus.ADMITTED

    response = client.post(
        f"{base}/record-response/", {"_form_submitted": "1", "response": "accept", "reason": "By phone"}
    )
    assert response.status_code == 302
    application.refresh_from_db()
    assert application.status == ApplicationStatus.CONFIRMED

    term = TermFactory(published=True)
    response = client.post(f"{base}/matriculate/", {"_form_submitted": "1", "admission_term": str(term.pk)})
    assert response.status_code == 302
    application.refresh_from_db()
    assert application.student_record_id is not None
    assert response["Location"] == f"/admin/person/studentrecord/{application.student_record_id}/change/"


def test_matriculates_confirmed_applications_in_bulk(manager: User) -> None:
    confirmed = list(
        Application.objects.filter(status=ApplicationStatus.CONFIRMED, student_record__isnull=True).values_list(
            "pk", flat=True
        )
    )
    submitted = Application.objects.filter(status=ApplicationStatus.SUBMITTED).values_list("pk", flat=True)[0]
    term = TermFactory(published=True)
    client = signed_in(manager)
    selected = [str(pk) for pk in [*confirmed, submitted]]

    form = client.post(
        "/admin/admission/application/", {"action": "matriculate_selected", "_selected_action": selected}
    )
    assert form.status_code == 200
    response = client.post(
        "/admin/admission/application/",
        {"action": "matriculate_selected", "_selected_action": selected, "apply": "1", "admission_term": term.pk},
    )
    assert response.status_code == 302
    assert StudentRecord.objects.filter(application__pk__in=confirmed).count() == len(confirmed)
    assert not StudentRecord.objects.filter(application__pk=submitted).exists()


def test_shows_open_cycles_publicly_and_the_applicant_their_applications() -> None:
    rolling = AdmissionCycle.objects.get(code="DEMO-ROLLING")
    assert escape(str(rolling.name)) in Client().get("/admissions/").content.decode()

    applicant = User.objects.get(email="admitted@demo.test")
    application = Application.objects.get(person_id=applicant.person_id)
    client = signed_in(applicant)

    listing = client.get("/portal/applications/")
    assert listing.status_code == 200
    assert str(ApplicationStatus.ADMITTED.label) in listing.content.decode()
    detail = client.get(f"/portal/applications/{application.pk}/")
    assert detail.status_code == 200
    assert "Accept the offer" in detail.content.decode()

    other = Application.objects.exclude(person_id=applicant.person_id).first()
    assert other is not None
    assert client.get(f"/portal/applications/{other.pk}/").status_code == 404


def test_lets_only_the_applicant_and_staff_in_scope_download_documents(diploma: Any) -> None:
    from ninefruits.admission.actions import AttachApplicationDocument

    from .support import PDF_BYTES, fake_pdf

    applicant = User.objects.get(email="applicant@demo.test")
    application = Application.objects.get(person_id=applicant.person_id)
    Application.objects.filter(pk=application.pk).update(
        status=ApplicationStatus.DRAFT, submitted_at=None, application_number=None
    )
    application.refresh_from_db()
    media = AttachApplicationDocument().handle(application, diploma.pk, fake_pdf(), applicant)
    url = f"/applications/{application.pk}/documents/{media.pk}/"

    response = signed_in(applicant).get(url)
    assert response.status_code == 200
    assert b"".join(response.streaming_content) == PDF_BYTES
    assert response["Cache-Control"] == "private, no-store"
    assert signed_in(User.objects.get(email="admitted@demo.test")).get(url).status_code == 404
    assert signed_in(UserFactory(permissions=[Permission.APPLICATIONS_VIEW])).get(url).status_code == 200


def test_shows_what_is_missing_when_an_incomplete_application_is_submitted_in_the_portal() -> None:
    from ninefruits.admission.actions import StartApplication

    applicant = User.objects.get(email="applicant@demo.test")
    rolling = AdmissionCycle.objects.get(code="DEMO-ROLLING")
    application = StartApplication().handle(applicant, rolling, rolling.programs.first().program)
    client = signed_in(applicant)

    page = client.get(f"/portal/applications/{application.pk}/")
    assert page.status_code == 200
    assert "Submit application" in page.content.decode()

    response = client.post(
        f"/portal/applications/{application.pk}/",
        {"action": "submit", "family_name": "Kim", "program_id": application.program_id, "previous_school_name": ""},
    )
    assert response.status_code == 422
    body = response.content.decode()
    assert "This field is required to submit." in body
    assert "Upload the required documents" in body
    application.refresh_from_db()
    assert application.status == ApplicationStatus.DRAFT

    assert client.post(f"/portal/applications/{application.pk}/", {"action": "withdraw"}).status_code == 302
    application.refresh_from_db()
    assert application.status == ApplicationStatus.WITHDRAWN
