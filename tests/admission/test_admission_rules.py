"""Original tests/Feature/Admission/AdmissionRulesTest.php."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from io import StringIO
from typing import Any

import pytest
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import Client
from django.utils import timezone

from ninefruits.admission.actions import (
    DecideApplication,
    MatriculateApplicant,
    ReleaseDecisions,
    RespondToOffer,
    StartApplication,
    SubmitApplication,
    WithdrawApplication,
)
from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import Application
from ninefruits.person.actions import MergePeople
from ninefruits.security.enums import Permission, ScopeType
from ninefruits.security.models import User
from tests.factories.admission import AdmissionCycleFactory, ApplicationFactory
from tests.factories.organization import ProgramFactory
from tests.factories.person import PersonFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("admission_reference")]


@pytest.fixture
def world(diploma: Any) -> dict[str, Any]:
    program = ProgramFactory()
    other = ProgramFactory()
    cycle = AdmissionCycleFactory(programs=[program, other], documents=[diploma])
    return {
        "program": program,
        "other_program": other,
        "cycle": cycle,
        "applicant": UserFactory(person=PersonFactory(), name=None),
        "reviewer": UserFactory(
            permissions=[
                Permission.APPLICATIONS_VIEW,
                Permission.APPLICATIONS_REVIEW,
                Permission.APPLICATIONS_MATRICULATE,
            ]
        ),
    }


def errors_of(callback: Callable[[], Any]) -> list[str]:
    try:
        callback()
    except ValidationError as error:
        return list(error.message_dict)
    return []


def decision_mails_to(user: User) -> int:
    return sum(
        1 for message in mail.outbox if user.email in message.to and "Decision on application" in message.subject
    )


def test_allows_one_open_application_per_cycle_and_only_to_offered_programs_in_open_cycles(
    world: dict[str, Any],
) -> None:
    start = StartApplication()
    applicant, cycle = world["applicant"], world["cycle"]
    not_offered = ProgramFactory()

    assert errors_of(lambda: start.handle(applicant, cycle, not_offered)) == ["program_id"]

    first = start.handle(applicant, cycle, world["program"])
    assert errors_of(lambda: start.handle(applicant, cycle, world["other_program"])) == ["admission_cycle_id"]

    WithdrawApplication().handle(first, applicant)
    assert start.handle(applicant, cycle, world["other_program"]).status == ApplicationStatus.DRAFT

    closed = AdmissionCycleFactory(closed=True, programs=[world["program"]])
    unpublished = AdmissionCycleFactory(programs=[world["program"]], is_published=False)
    assert errors_of(lambda: start.handle(applicant, closed, world["program"])) == ["admission_cycle_id"]
    assert errors_of(lambda: start.handle(applicant, unpublished, world["program"])) == ["admission_cycle_id"]


def test_refuses_to_submit_incomplete_applications(world: dict[str, Any]) -> None:
    application = StartApplication().handle(world["applicant"], world["cycle"], world["program"])

    assert errors_of(lambda: SubmitApplication().handle(application, world["applicant"])) == [
        "previous_school_name",
        "personal_statement",
        "documents",
    ]


def test_keeps_decisions_changeable_and_hidden_until_released_then_notifies_once(
    world: dict[str, Any], django_capture_on_commit_callbacks: Any
) -> None:
    applicant, reviewer = world["applicant"], world["reviewer"]
    application = ApplicationFactory(
        admission_cycle=world["cycle"], program=world["program"], submitted=True, person=applicant.person
    )
    decide = DecideApplication()

    decide.reject(application, reviewer, "Capacity")
    decide.admit(application, reviewer, "Reconsidered")
    assert application.applicant_status() == ApplicationStatus.UNDER_REVIEW

    with django_capture_on_commit_callbacks(execute=True):
        assert ReleaseDecisions().handle([application, application], reviewer) == 1
    assert decision_mails_to(applicant) == 1

    application.refresh_from_db()
    assert errors_of(lambda: decide.reject(application, reviewer, "Too late")) == ["status"]


def test_releases_immediately_in_cycles_that_say_so(
    world: dict[str, Any], django_capture_on_commit_callbacks: Any
) -> None:
    applicant = world["applicant"]
    rolling = AdmissionCycleFactory(rolling=True, programs=[world["program"]])
    application = ApplicationFactory(
        admission_cycle=rolling, program=world["program"], submitted=True, person=applicant.person
    )

    with django_capture_on_commit_callbacks(execute=True):
        DecideApplication().admit(application, world["reviewer"])

    application.refresh_from_db()
    assert application.decision_released_at is not None
    assert decision_mails_to(applicant) == 1


def test_limits_reviewers_to_their_scope_and_keeps_applicants_out_of_staff_decisions(world: dict[str, Any]) -> None:
    applicant = world["applicant"]
    application = ApplicationFactory(
        admission_cycle=world["cycle"], program=world["program"], submitted=True, person=applicant.person
    )
    other_unit_reviewer = UserFactory(
        permissions=[Permission.APPLICATIONS_REVIEW],
        permissions__scope_type=ScopeType.ORG_UNIT,
        permissions__scope_id=world["other_program"].org_unit_id,
    )

    with pytest.raises(PermissionDenied):
        DecideApplication().admit(application, other_unit_reviewer)
    with pytest.raises(PermissionDenied):
        DecideApplication().admit(application, applicant)
    with pytest.raises(PermissionDenied):
        MatriculateApplicant().handle(application, TermFactory(published=True), other_unit_reviewer)


def test_accepts_offers_only_before_the_deadline_and_lets_staff_record_a_late_answer_with_a_reason(
    world: dict[str, Any],
) -> None:
    applicant, reviewer = world["applicant"], world["reviewer"]
    application = ApplicationFactory(
        admission_cycle=world["cycle"], program=world["program"], admitted=True, released=True, person=applicant.person
    )
    application.offer_expires_at = timezone.now() - timedelta(minutes=1)
    application.save()
    respond = RespondToOffer()

    assert errors_of(lambda: respond.handle(application, True, applicant)) == ["status"]
    assert errors_of(lambda: respond.handle(application, True, reviewer)) == ["reason"]

    respond.handle(application, True, reviewer, "Accepted by phone on the deadline day")
    application.refresh_from_db()
    assert application.status == ApplicationStatus.CONFIRMED


def test_matriculates_only_confirmed_applications_once(world: dict[str, Any]) -> None:
    reviewer = world["reviewer"]
    term = TermFactory(published=True)
    admitted = ApplicationFactory(
        admission_cycle=world["cycle"],
        program=world["program"],
        admitted=True,
        released=True,
        person=world["applicant"].person,
    )

    assert errors_of(lambda: MatriculateApplicant().handle(admitted, term, reviewer)) == ["status"]

    admitted.status = ApplicationStatus.CONFIRMED
    admitted.save()
    MatriculateApplicant().handle(admitted, term, reviewer)

    admitted.refresh_from_db()
    assert errors_of(lambda: MatriculateApplicant().handle(admitted, term, reviewer)) == ["status"]


def test_hides_registration_when_the_institution_turns_it_off(set_admission_settings: Any) -> None:
    set_admission_settings(applicant_registration_enabled=False)
    client = Client()

    assert client.get("/accounts/signup/").status_code == 404
    response = client.post(
        "/accounts/signup/",
        {
            "family_name": "X",
            "email": "x@example.test",
            "password1": "correct-horse-battery",
            "password2": "correct-horse-battery",
        },
    )
    assert response.status_code == 404
    assert not User.objects.filter(email="x@example.test").exists()


def test_expires_stale_drafts_and_drafts_of_closed_cycles(world: dict[str, Any]) -> None:
    program, other = world["program"], world["other_program"]
    closed = AdmissionCycleFactory(closed=True, programs=[program])
    in_closed = ApplicationFactory(admission_cycle=closed, program=program)
    fresh = ApplicationFactory(admission_cycle=world["cycle"], program=program)
    stale = ApplicationFactory(admission_cycle=world["cycle"], program=other)
    Application.objects.filter(pk=stale.pk).update(updated_at=timezone.now() - timedelta(days=200))

    out = StringIO()
    assert call_command("admission_expire_drafts", "--dry-run", stdout=out) == 0
    assert "2 draft(s)" in out.getvalue()
    assert call_command("admission_expire_drafts", stdout=StringIO()) == 0

    for application, status in ((in_closed, "expired"), (stale, "expired"), (fresh, "draft")):
        application.refresh_from_db()
        assert application.status == status


def test_expires_drafts_from_the_scheduled_task(world: dict[str, Any]) -> None:
    from ninefruits.admission.tasks import expire_drafts

    closed = AdmissionCycleFactory(closed=True, programs=[world["program"]])
    draft = ApplicationFactory(admission_cycle=closed, program=world["program"])

    expire_drafts.apply()

    draft.refresh_from_db()
    assert draft.status == ApplicationStatus.EXPIRED


def test_matriculates_a_cycle_from_the_command_line(world: dict[str, Any]) -> None:
    TermFactory(published=True, code="2027-SP")
    cycle, program = world["cycle"], world["program"]
    confirmed = [ApplicationFactory(admission_cycle=cycle, program=program, confirmed=True) for _ in range(2)]
    actor = UserFactory(permissions=[Permission.APPLICATIONS_MATRICULATE], email="admissions@example.test")

    def records() -> list[Any]:
        return [
            record
            for record in Application.objects.filter(pk__in=[a.pk for a in confirmed]).values_list(
                "student_record_id", flat=True
            )
            if record
        ]

    assert (
        call_command("admission_matriculate", cycle.code, "--term=2027-SP", stdout=StringIO(), stderr=StringIO()) == 1
    )
    out = StringIO()
    assert (
        call_command(
            "admission_matriculate", cycle.code, "--term=2027-SP", f"--actor={actor.email}", "--dry-run", stdout=out
        )
        == 0
    )
    assert "2 confirmed applicant(s)" in out.getvalue()
    assert records() == []

    assert (
        call_command("admission_matriculate", cycle.code, "--term=2027-SP", f"--actor={actor.email}", stdout=StringIO())
        == 0
    )
    assert len(records()) == 2


def test_moves_applications_when_merging_a_duplicate_applicant_into_an_earlier_person(world: dict[str, Any]) -> None:
    graduate = PersonFactory()
    duplicate = PersonFactory()
    application = ApplicationFactory(
        admission_cycle=world["cycle"], program=world["program"], submitted=True, person=duplicate
    )
    registrar = UserFactory(permissions=[Permission.PEOPLE_MANAGE, Permission.PEOPLE_MERGE])

    MergePeople().handle(duplicate, graduate, "Same person: applied with a new account", registrar)

    application.refresh_from_db()
    assert application.person_id == graduate.pk

    other = PersonFactory()
    ApplicationFactory(admission_cycle=world["cycle"], program=world["other_program"], submitted=True, person=other)

    assert errors_of(lambda: MergePeople().handle(other, graduate, "Same person", registrar)) == ["target_id"]
