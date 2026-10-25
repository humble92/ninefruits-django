"""Original tests/Feature/Person/StudentRecordActionsTest.php."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

import pytest
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.utils import timezone

from ninefruits.audit.models import ActivityLog, RecordChange
from ninefruits.core.targeting import TargetCriteria
from ninefruits.person.actions import (
    AcceptInvitation,
    AssignAdvisor,
    CancelStatusChange,
    DecideStatusChange,
    InvitePerson,
    MergePeople,
    RecordStatusChange,
    RegisterStudent,
    RequestStatusChange,
)
from ninefruits.person.enums import StatusChangeStatus, StudentStatus
from ninefruits.person.models import Person, StudentStatusChangeType
from ninefruits.security.enums import Permission, Persona
from ninefruits.security.models import RoleAssignment, User
from ninefruits.security.services.personas import PersonaResolver, registered_detectors
from tests.factories.organization import ProgramFactory
from tests.factories.person import InstructorFactory, PersonFactory, StudentRecordFactory
from tests.factories.security import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("status_change_types")]


@pytest.fixture
def program() -> Any:
    return ProgramFactory(effective_start_date=date(2000, 1, 1))


@pytest.fixture
def staff() -> User:
    return UserFactory(
        permissions=[
            Permission.STUDENT_RECORDS_MANAGE,
            Permission.STUDENT_STATUS_CHANGES_APPROVE,
            Permission.PEOPLE_MANAGE,
            Permission.PEOPLE_MERGE,
        ]
    )


def change_type(code: str) -> StudentStatusChangeType:
    return StudentStatusChangeType.objects.get(code=code)


def test_registers_students_with_numbers_from_the_configured_pattern(
    program: Any, staff: User, set_student_record_settings: Any
) -> None:
    set_student_record_settings(student_number_pattern="S{YY}{SEQ:4}")

    first = RegisterStudent().handle(PersonFactory(), program, {"admission_date": "2026-03-02"}, staff)
    second = RegisterStudent().handle(PersonFactory(), program, {"admission_date": "2026-03-02"}, staff)

    assert first.student_number == "S260001"
    assert second.student_number == "S260002"
    assert first.org_unit_id == program.org_unit_id
    assert first.catalog_year == 2026
    assert ActivityLog.objects.filter(event="student_record.registered").count() == 2


def test_skips_numbers_already_taken_by_imported_records(program: Any) -> None:
    StudentRecordFactory(program=program, student_number="202600001")

    record = RegisterStudent().handle(PersonFactory(), program, {"admission_date": "2026-03-02"})

    assert record.student_number == "202600002"


def test_gives_a_returning_graduate_a_new_record_and_number_keeping_the_old_one(program: Any) -> None:
    alumnus = StudentRecordFactory(program=program, graduated=True, admission_date=date(2018, 3, 1))

    new = RegisterStudent().handle(alumnus.person, program, {"admission_date": "2026-03-02"})

    alumnus.refresh_from_db()
    assert new.person_id == alumnus.person_id
    assert new.student_number != alumnus.student_number
    assert alumnus.status == StudentStatus.GRADUATED
    assert alumnus.person.student_records.count() == 2


def test_lets_a_student_request_a_leave_that_another_staff_member_approves(program: Any, staff: User) -> None:
    record = StudentRecordFactory(program=program)
    student = UserFactory(person=record.person)

    change = RequestStatusChange().handle(
        record, change_type("leave_of_absence"), date(2026, 9, 1), "Military service", student
    )

    with pytest.raises(ValidationError):
        RequestStatusChange().handle(record, change_type("withdrawal"), date(2026, 9, 1), "again", student)

    DecideStatusChange().approve(change, staff, "Documents checked")

    record.refresh_from_db()
    change.refresh_from_db()
    assert record.status == StudentStatus.ON_LEAVE
    assert change.status == StatusChangeStatus.APPROVED
    assert change.decided_by_id == staff.pk


def test_does_not_let_anyone_decide_their_own_request(program: Any) -> None:
    record = StudentRecordFactory(program=program)
    student = UserFactory(person=record.person)
    RoleAssignment.objects.filter(user=student).delete()
    change = RequestStatusChange().handle(
        record, change_type("withdrawal"), timezone.localdate(), "Moving abroad", student
    )

    with pytest.raises(PermissionDenied):
        DecideStatusChange().approve(change, student)


def test_rejects_requests_that_do_not_fit_the_current_status_or_are_staff_only(program: Any) -> None:
    record = StudentRecordFactory(program=program)
    student = UserFactory(person=record.person)

    with pytest.raises(ValidationError):
        RequestStatusChange().handle(record, change_type("return_from_leave"), timezone.localdate(), "x", student)
    with pytest.raises(ValidationError):
        RequestStatusChange().handle(record, change_type("dismissal"), timezone.localdate(), "x", student)


def test_lets_the_requester_cancel_and_records_staff_decisions_directly(program: Any, staff: User) -> None:
    record = StudentRecordFactory(program=program)
    student = UserFactory(person=record.person)
    change = RequestStatusChange().handle(record, change_type("leave_of_absence"), timezone.localdate(), "x", student)

    CancelStatusChange().handle(change, student)
    RecordStatusChange().handle(
        record, change_type("dismissal"), date(2026, 10, 1), "Disciplinary committee decision", staff
    )

    activity = ActivityLog.objects.get(event="student_status_change.recorded")
    change.refresh_from_db()
    record.refresh_from_db()
    assert change.status == StatusChangeStatus.CANCELLED
    assert record.status == StudentStatus.DISMISSED
    assert activity.reason == "Disciplinary committee decision"
    assert RecordChange.objects.filter(
        table_name="student_records", record_id=str(record.pk), operation="UPDATE"
    ).exists()


def test_sets_the_graduation_date_when_graduating(program: Any, staff: User) -> None:
    record = StudentRecordFactory(program=program)

    RecordStatusChange().handle(record, change_type("graduation"), date(2027, 2, 20), "Degree conferred", staff)

    record.refresh_from_db()
    assert record.graduation_date == date(2027, 2, 20)


def test_ends_the_current_primary_advisor_when_assigning_a_new_one(program: Any) -> None:
    record = StudentRecordFactory(program=program)
    first, second = InstructorFactory(), InstructorFactory()

    AssignAdvisor().handle(record, first, date(2026, 3, 1))
    AssignAdvisor().handle(record, second, date(2026, 9, 1))

    history = list(record.advisor_assignments.order_by("start_date"))
    assert [assignment.instructor_id for assignment in history] == [first.pk, second.pk]
    assert history[0].end_date == date(2026, 8, 31)
    assert history[-1].end_date is None


def test_invites_a_person_and_creates_a_verified_account_from_the_link(
    staff: User, django_capture_on_commit_callbacks: Any
) -> None:
    person = PersonFactory()

    with django_capture_on_commit_callbacks(execute=True):
        InvitePerson().handle(person, "New.Student@Example.test", staff)

    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new.student@example.test"]
    token = re.search(r"/invitations/([^/\s]+)/", mail.outbox[0].body).group(1)  # type: ignore[union-attr]

    client = Client()
    response = client.get(f"/invitations/{token}/")
    assert response.status_code == 200
    assert "new.student@example.test" in response.content.decode()

    password = "Correct-Horse-Battery-9"
    response = client.post(f"/invitations/{token}/", {"password": password, "password_confirmation": password})
    assert response.status_code == 302
    assert response["Location"] == "/portal/"

    user = User.objects.get(email="new.student@example.test")
    assert user.person_id == person.pk
    assert user.email_verified_at is not None
    assert AcceptInvitation.find(token) is None


def test_merges_a_duplicate_person_into_another(program: Any, staff: User) -> None:
    target = PersonFactory(phone=None)
    duplicate = PersonFactory(national_id="TEST-123", phone="010-1111-2222")
    record = StudentRecordFactory(program=program, person=duplicate)
    account = UserFactory(person=duplicate)

    MergePeople().handle(duplicate, target, "Registered twice", staff)

    record.refresh_from_db()
    account.refresh_from_db()
    target = Person.objects.get(pk=target.pk)
    duplicate.refresh_from_db()
    assert record.person_id == target.pk
    assert account.person_id == target.pk
    assert target.phone == "010-1111-2222"
    assert target.national_id_encrypted == "TEST-123"
    assert target.pk in Person.objects.where_pii("national_id", "TEST-123").values_list("pk", flat=True)
    assert duplicate.merged_into_id == target.pk


def test_derives_personas_from_records(program: Any) -> None:
    current = StudentRecordFactory(program=program)
    StudentRecordFactory(program=program, graduated=True, person=current.person)
    instructor = InstructorFactory()
    AssignAdvisor().handle(current, instructor, timezone.localdate() - timedelta(days=1))

    student = UserFactory(person=current.person)
    professor = UserFactory(person=instructor.person)

    resolver = PersonaResolver(registered_detectors())
    assert set(resolver.personas_for(student)) == {Persona.STUDENT, Persona.ALUMNI}
    assert set(resolver.personas_for(professor)) == {Persona.INSTRUCTOR, Persona.ADVISOR}


def test_provides_the_student_as_a_target_for_term_window_eligibility(program: Any) -> None:
    record = StudentRecordFactory(program=program, year_level=4, admission_date=date(2023, 3, 1), tags=["exchange"])

    assert TargetCriteria(
        year_levels=[4], admission_year_from=2023, org_unit_ids=[program.org_unit_id], tags=["exchange"]
    ).matches(record)
    assert not TargetCriteria(year_levels=[1]).matches(record)
