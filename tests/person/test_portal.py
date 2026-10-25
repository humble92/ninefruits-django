"""Original tests/Feature/Person/PortalTest.php (my records, my details, advisees; the SSO unlink
case is in tests/security/test_security_page.py)."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.utils import timezone
from django.utils.html import escape

from ninefruits.core.db import session_context
from ninefruits.person.enums import StatusChangeStatus, StudentStatus
from ninefruits.person.models import Guardian, Person, StudentRecord, StudentStatusChange, StudentStatusChangeType
from ninefruits.security.enums import MfaEnforcement
from ninefruits.security.models import User
from ninefruits.settings.groups.security import SecuritySettings
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("demo_people")]


@pytest.fixture
def demo_people(essential_data: None) -> None:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()
    DemoReferenceSeeder()()
    DemoPeopleSeeder()()


def demo_user(local: str) -> User:
    return User.objects.get(email=f"{local}@demo.test")


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def test_shows_each_persona_its_own_pages_under_row_level_security() -> None:
    student = demo_user("student")
    own = StudentRecord.objects.filter(person_id=student.person_id).values_list("student_number", flat=True)[0]
    other = StudentRecord.objects.exclude(person_id=student.person_id).values_list("student_number", flat=True)[0]
    instructor = demo_user("instructor")
    name = Person.objects.get(pk=student.person_id).display_name()
    session_context().use_baseline({})

    client = signed_in(student)
    home = client.get("/portal/").content.decode()
    assert escape(name) in home  # the welcome uses the person's name
    assert "My records" in home
    assert "Advisees" not in home
    records = client.get("/portal/records/")
    assert records.status_code == 200
    assert own in records.content.decode()
    assert other not in records.content.decode()
    assert client.get("/portal/profile/").status_code == 200

    client = signed_in(instructor)
    assert "Advisees" in client.get("/portal/").content.decode()
    advisees = client.get("/portal/advisees/")
    assert advisees.status_code == 200
    assert own in advisees.content.decode()


def test_lets_a_student_request_a_leave_of_absence_and_cancel_it() -> None:
    student = demo_user("student")
    record = StudentRecord.objects.get(person_id=student.person_id)
    leave = StudentStatusChangeType.objects.get(code="leave_of_absence")
    client = signed_in(student)

    assert str(leave.name) in client.get("/portal/records/").content.decode()
    client.post(
        "/portal/records/",
        {
            "action": "request_change",
            "status_change_type": str(leave.pk),
            "effective_date": timezone.localdate().isoformat(),
            "reason": "Family matters",
        },
    )
    assert "Cancel request" in client.get("/portal/records/").content.decode()

    change = StudentStatusChange.objects.get(student_record=record)
    assert change.status == StatusChangeStatus.REQUESTED
    assert change.requested_by_id == student.pk

    client.post("/portal/records/", {"action": "cancel", "change_id": str(change.pk)})

    change.refresh_from_db()
    record.refresh_from_db()
    assert change.status == StatusChangeStatus.CANCELLED
    assert record.status == StudentStatus.ENROLLED


def test_does_not_let_a_student_cancel_someone_elses_request() -> None:
    someone = StudentStatusChange.objects.filter(status=StatusChangeStatus.REQUESTED).first()
    assert someone is not None

    response = signed_in(demo_user("student")).post(
        "/portal/records/", {"action": "cancel", "change_id": str(someone.pk)}
    )

    assert response.status_code == 404


def test_lets_a_readmitted_graduate_switch_records_and_only_request_on_the_current_one() -> None:
    user = demo_user("readmitted")
    records = list(StudentRecord.objects.filter(person_id=user.person_id).order_by("admission_date"))
    assert len(records) == 2
    client = signed_in(user)

    page = client.get("/portal/records/").content.decode()
    assert "You have more than one student record. Choose one:" in page
    assert "Request a status change" in page

    client.post("/portal/records/", {"action": "choose", "record_id": str(records[0].pk)})
    page = client.get("/portal/records/").content.decode()
    assert str(StudentStatus(records[0].status).label) in page
    assert "Request a status change" not in page


def test_lets_a_graduate_see_records_read_only() -> None:
    page = signed_in(demo_user("alumni")).get("/portal/records/").content.decode()

    assert "Graduated" in page
    assert "Request a status change" not in page


def test_updates_own_contact_details_and_guardians_but_not_the_name() -> None:
    student = demo_user("student")
    person = Person.objects.get(pk=student.person_id)
    family_name = person.family_name
    client = signed_in(student)

    client.post("/portal/profile/", {"action": "save_contact", "phone": "010-1234-5678", "family_name": "Changed"})
    client.post("/portal/profile/", {"action": "add_guardian", "full_name": "Kim Mother", "relationship": "mother"})

    person.refresh_from_db()
    guardian = Guardian.objects.get(person=person, full_name="Kim Mother")
    assert person.phone == "010-1234-5678"
    assert person.family_name == family_name

    foreign = Guardian.objects.exclude(person=person).first()
    assert foreign is not None
    assert (
        client.post("/portal/profile/", {"action": "remove_guardian", "guardian_id": str(foreign.pk)}).status_code
        == 404
    )
    client.post("/portal/profile/", {"action": "remove_guardian", "guardian_id": str(guardian.pk)})

    assert not Guardian.objects.filter(pk=guardian.pk).exists()


def test_hides_the_records_page_from_accounts_without_a_person(django_user_model: Any) -> None:
    from tests.factories.security import UserFactory

    assert signed_in(UserFactory()).get("/portal/records/").status_code == 404
