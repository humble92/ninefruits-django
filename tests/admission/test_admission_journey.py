"""Original tests/Feature/Admission/AdmissionJourneyTest.php (Phase 3 completion criteria: one
account from registration to a student who can register for courses; a graduate applying again
keeps the earlier record)."""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

import pytest
from django.core import mail
from django.test import Client
from django.utils import timezone

from ninefruits.admission.actions import DecideApplication, MatriculateApplicant
from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import AdmissionCycle, Application
from ninefruits.audit.models import ActivityLog
from ninefruits.core.targeting import TargetCriteria
from ninefruits.organization.models import Program
from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentRecord
from ninefruits.security.enums import Permission, Persona
from ninefruits.security.models import User
from ninefruits.security.services.authorization import authorization
from ninefruits.term.enums import TermWindowType
from ninefruits.term.services.term_resolver import TermResolver
from tests.factories.admission import AdmissionCycleFactory
from tests.factories.organization import ProgramFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory, TermWindowFactory

from .support import fake_pdf

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("admission_reference", "mfa_disabled")]

PASSWORD = "correct-horse-battery"


@pytest.fixture
def world(diploma: Any) -> dict[str, Any]:
    program = ProgramFactory()
    today = timezone.localdate()
    return {
        "program": program,
        "diploma": diploma,
        "cycle": AdmissionCycleFactory(code="2027-REG", programs=[program], documents=[diploma], offer_response_days=7),
        "term": TermFactory(
            published=True,
            code="2027-SP",
            start_date=today + timedelta(days=60),
            end_date=today + timedelta(days=180),
        ),
        "officer": UserFactory(
            permissions=[
                Permission.ADMIN_PANEL_ACCESS,
                Permission.APPLICATIONS_VIEW,
                Permission.APPLICATIONS_REVIEW,
                Permission.APPLICATIONS_MATRICULATE,
            ]
        ),
    }


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def submitted_application(
    client: Client, user: User, cycle: AdmissionCycle, program: Program, document: Any, capture: Any
) -> Application:
    response = client.post("/portal/applications/", {"cycle": cycle.pk, "program": program.pk})
    application = Application.objects.get(person_id=user.person_id, admission_cycle=cycle)
    assert response.status_code == 302
    assert response["Location"] == f"/portal/applications/{application.pk}/"

    person = application.person
    with capture(execute=True):
        response = client.post(
            f"/portal/applications/{application.pk}/",
            {
                "action": "submit",
                "family_name": person.family_name,
                "given_name": person.given_name or "",
                "birth_date": "2007-04-05",
                "program_id": program.pk,
                "previous_school_name": "Hanbit High School",
                "personal_statement": "I want to study here.",
                f"document_{document.pk}": fake_pdf("diploma.pdf"),
            },
        )
    assert response.status_code == 302, response.content.decode()[:2000]
    application.refresh_from_db()
    return application


def test_takes_one_account_from_registration_to_a_student_who_can_register_for_courses(
    world: dict[str, Any], django_capture_on_commit_callbacks: Any
) -> None:
    cycle, program, term, officer = world["cycle"], world["program"], world["term"], world["officer"]
    visitor = Client()

    # Registration and email verification
    response = visitor.post(
        "/accounts/signup/",
        {
            "family_name": "Kim",
            "given_name": "Minji",
            "email": "minji@example.test",
            "password1": PASSWORD,
            "password2": PASSWORD,
        },
    )
    assert response.status_code == 302
    user = User.objects.get(email="minji@example.test")
    assert user.person.family_name == "Kim"
    assert not user.has_verified_email()
    verification = next(message for message in mail.outbox if "minji@example.test" in message.to)
    link = re.search(r"/accounts/confirm-email/([^/\s]+)/", verification.body)
    assert link is not None

    applicant = visitor  # signed in by the sign-up
    response = applicant.get("/portal/applications/")
    assert response.status_code == 302
    assert response["Location"] == "/admissions/verify-email/"
    applicant.post(f"/accounts/confirm-email/{link.group(1)}/")
    user.refresh_from_db()
    assert user.has_verified_email()
    response = applicant.get("/portal/applications/")
    assert response.status_code == 200
    assert str(cycle.name) in response.content.decode()

    # Application
    mail.outbox.clear()
    application = submitted_application(
        applicant, user, cycle, program, world["diploma"], django_capture_on_commit_callbacks
    )
    authorization().flush()

    assert application.status == ApplicationStatus.SUBMITTED
    assert application.application_number == "2027-REG-00001"
    assert str(application.person.birth_date) == "2007-04-05"
    assert application.get_media(Application.DOCUMENTS_COLLECTION).count() == 1
    assert Persona.APPLICANT in authorization().personas.personas_for(user)
    assert any("Application 2027-REG-00001 received" in message.subject for message in mail.outbox)

    # Decision, hidden until released
    mail.outbox.clear()
    with django_capture_on_commit_callbacks(execute=True):
        DecideApplication().admit(application, officer, "Strong statement")
    application.refresh_from_db()
    assert application.applicant_status() == ApplicationStatus.UNDER_REVIEW
    assert mail.outbox == []

    # Staff use their own browser session.
    staff = signed_in(officer)
    assert staff.get(f"/admin/admission/application/{application.pk}/change/").status_code == 200
    with django_capture_on_commit_callbacks(execute=True):
        response = staff.post(f"/admin/admission/application/{application.pk}/release/", {"_form_submitted": "1"})
    assert response.status_code == 302

    application.refresh_from_db()
    assert application.applicant_status() == ApplicationStatus.ADMITTED
    assert application.offer_expires_at is not None
    assert any(user.email in message.to and "Decision on application" in message.subject for message in mail.outbox)

    # Offer accepted by the applicant, then matriculation
    response = applicant.post(f"/portal/applications/{application.pk}/", {"action": "respond", "accept": "1"})
    assert response.status_code == 302
    application.refresh_from_db()
    assert application.status == ApplicationStatus.CONFIRMED

    record = MatriculateApplicant().handle(application, term, officer)

    assert record.person_id == user.person_id
    assert record.admission_term_id == term.pk
    assert record.admission_date == term.start_date
    application.refresh_from_db()
    assert application.student_record_id == record.pk
    assert ActivityLog.objects.filter(event="application.matriculated", causer_id=officer.pk).exists()

    # Same account, now a student: signs in with the same email and is eligible for the freshman
    # registration window.
    authorization().flush()
    user.refresh_from_db()
    personas = authorization().personas.personas_for(user)
    assert Persona.STUDENT in personas
    assert Persona.APPLICANT not in personas

    TermWindowFactory(
        term=term,
        window_type=TermWindowType.REGISTRATION,
        eligibility=TargetCriteria(year_levels=[1], student_statuses=["enrolled"]),
    )
    assert [found.pk for found in TermResolver().terms_open_for(TermWindowType.REGISTRATION, record)] == [term.pk]

    again = Client()
    response = again.post("/accounts/login/", {"login": "minji@example.test", "password": PASSWORD})
    assert response.status_code == 302
    assert response["Location"] == "/portal/"
    records = again.get("/portal/records/")
    assert records.status_code == 200
    assert record.student_number in records.content.decode()


def test_lets_a_graduate_apply_again_with_the_same_account_and_keeps_the_earlier_record(
    world: dict[str, Any], django_capture_on_commit_callbacks: Any
) -> None:
    program, officer = world["program"], world["officer"]
    earlier = StudentRecordFactory(program=program, graduated=True, student_number="201900001")
    graduate = UserFactory(person=earlier.person)
    client = signed_in(graduate)

    application = submitted_application(
        client, graduate, world["cycle"], program, world["diploma"], django_capture_on_commit_callbacks
    )
    # Identity is the registrar's once a record exists.
    assert str(application.person.birth_date) != "2007-04-05"

    DecideApplication().admit(application, officer)
    Application.objects.filter(pk=application.pk).update(decision_released_at=timezone.now())
    client.post(f"/portal/applications/{application.pk}/", {"action": "respond", "accept": "1"})
    application.refresh_from_db()
    record = MatriculateApplicant().handle(application, world["term"], officer)

    numbers = sorted(
        StudentRecord.objects.filter(person_id=graduate.person_id).values_list("student_number", flat=True)
    )
    assert numbers == sorted(["201900001", record.student_number])
    earlier.refresh_from_db()
    assert earlier.status == StudentStatus.GRADUATED
    assert User.objects.filter(person_id=graduate.person_id).count() == 1
