"""Original tests/Feature/Admin/PeopleAdminTest.php and the people datasets of
tests/Feature/Admin/AdminPagesTest.php."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from ninefruits.audit.models import SecurityEvent
from ninefruits.person.enums import AdditionalProgramRequestStatus, StatusChangeStatus, StudentStatus
from ninefruits.person.models import Instructor, Person, StudentRecord, StudentStatusChange
from ninefruits.security.enums import MfaEnforcement, Permission, ScopeType
from ninefruits.security.models import User
from ninefruits.settings.groups.security import SecuritySettings
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from tests.factories.person import PersonFactory, StudentRecordFactory
from tests.factories.security import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("essential_data", "demo_people")]


@pytest.fixture
def demo_people(essential_data: None) -> None:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()
    DemoReferenceSeeder()()
    DemoPeopleSeeder()()


@pytest.fixture
def manager() -> User:
    return UserFactory(permissions=list(Permission))


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def test_renders_every_people_and_student_record_page(manager: User) -> None:
    record = StudentRecord.objects.filter(person__user__isnull=True).first()
    assert record is not None
    instructor = Instructor.objects.first()
    assert instructor is not None
    pages = [
        "/admin/person/person/",
        "/admin/person/person/add/",
        f"/admin/person/person/{record.person_id}/change/",
        "/admin/person/person/?q=a",
        f"/admin/person/person/{record.person_id}/invite/",
        f"/admin/person/person/{record.person_id}/merge/",
        "/admin/person/studentrecord/",
        "/admin/person/studentrecord/add/",
        f"/admin/person/studentrecord/{record.pk}/change/",
        f"/admin/person/studentrecord/{record.pk}/record-status-change/",
        f"/admin/person/studentrecord/{record.pk}/assign-advisor/",
        "/admin/person/studentrecord/import-csv/",
        "/admin/person/studentrecord/?q=2",
        "/admin/person/studentstatuschange/",
        "/admin/person/studentstatuschangetype/",
        "/admin/person/studentstatuschangetype/add/",
        "/admin/person/additionalprogramrequest/",
        "/admin/person/instructor/",
        "/admin/person/instructor/add/",
        f"/admin/person/instructor/{instructor.pk}/change/",
        "/admin/person/instructor/import-csv/",
        "/admin/settings/authentication/",
        "/admin/settings/student-records/",
    ]
    client = signed_in(manager)
    for url in pages:
        response = client.get(url)
        assert response.status_code == 200, url


def test_limits_a_department_assistant_to_records_of_their_department() -> None:
    record = StudentRecord.objects.order_by("pk").first()
    assert record is not None
    other = StudentRecord.objects.exclude(org_unit_id=record.org_unit_id).first()
    assert other is not None
    assistant = UserFactory(
        permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.STUDENT_RECORDS_VIEW],
        permissions__scope_type=ScopeType.ORG_UNIT,
        permissions__scope_id=record.org_unit_id,
    )
    client = signed_in(assistant)

    assert client.get(f"/admin/person/studentrecord/{record.pk}/change/").status_code == 200
    assert client.get(f"/admin/person/studentrecord/{other.pk}/change/").status_code in (302, 404)
    assert client.get("/admin/person/studentrecord/add/").status_code == 403
    assert client.get("/admin/person/person/add/").status_code == 403


def test_approves_a_pending_request_from_the_status_change_list(manager: User) -> None:
    change = StudentStatusChange.objects.filter(status=StatusChangeStatus.REQUESTED).first()
    assert change is not None

    response = signed_in(manager).post(
        f"/admin/person/studentstatuschange/{change.pk}/approve/", {"_form_submitted": "1", "note": "Documents checked"}
    )

    assert response.status_code == 302
    change.refresh_from_db()
    assert change.status == StatusChangeStatus.APPROVED
    assert StudentRecord.objects.get(pk=change.student_record_id).status == StudentStatus.ON_LEAVE


def test_unlocks_a_locked_account_with_a_reason(manager: User) -> None:
    locked = UserFactory(locked_until=timezone.now() + timedelta(minutes=10))

    response = signed_in(manager).post(
        f"/admin/security/user/{locked.pk}/unlock/", {"_form_submitted": "1", "reason": "Verified by phone"}
    )

    assert response.status_code == 302
    locked.refresh_from_db()
    assert not locked.is_locked()


def test_shows_people_only_to_staff_allowed_to_see_them() -> None:
    nobody = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])

    assert signed_in(nobody).get("/admin/person/person/").status_code == 403
    assert Person.objects.count() > 0


def test_registers_a_student_for_a_new_person(manager: User) -> None:
    from ninefruits.organization.models import Program

    program = Program.objects.effective_on().order_by("code").first()
    assert program is not None
    response = signed_in(manager).post(
        "/admin/person/studentrecord/add/",
        {
            "person_mode": "new",
            "new_person_family_name": "Newcomer",
            "new_person_given_name": "Alex",
            "new_person_name_ko": "알렉스",
            "program": str(program.pk),
            "admission_date": timezone.localdate().isoformat(),
            "year_level": "1",
        },
    )

    assert response.status_code == 302
    record = StudentRecord.objects.get(person__family_name="Newcomer")
    assert record.person.name_variants == {"ko": "알렉스"}
    assert record.catalog_year == timezone.localdate().year


def test_reveals_a_national_id_once_and_records_it(manager: User) -> None:
    person = PersonFactory(national_id="TEST-5551234567")
    StudentRecordFactory(person=person)
    client = signed_in(manager)

    detail = client.get(f"/admin/person/person/{person.pk}/change/").content.decode()
    assert "TEST-5551234567" not in detail
    assert "**********4567" in detail

    response = client.post(
        f"/admin/person/person/{person.pk}/reveal-national-id/", {"_form_submitted": "1", "reason": "Identity check"}
    )

    assert response.status_code == 200
    assert "TEST-5551234567" in response.content.decode()
    assert "no-store" in response["Cache-Control"]
    event = SecurityEvent.objects.get(type="sensitive_data.revealed")
    assert event.properties == {"attribute": "national_id", "reason": "Identity check"}


def test_does_not_offer_reveals_without_the_sensitive_permission() -> None:
    person = PersonFactory(national_id="TEST-5551234567")
    viewer = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.PEOPLE_VIEW])

    response = signed_in(viewer).post(
        f"/admin/person/person/{person.pk}/reveal-national-id/", {"_form_submitted": "1", "reason": "x"}
    )

    assert response.status_code == 403
    assert not SecurityEvent.objects.filter(type="sensitive_data.revealed").exists()


def test_edits_a_person_and_keeps_the_national_id_when_left_empty(manager: User) -> None:
    person = PersonFactory(national_id="TEST-000111", family_name="Before")
    response = signed_in(manager).post(
        f"/admin/person/person/{person.pk}/change/",
        {
            "family_name": "After",
            "given_name": "Kim",
            "name_ko": "김",
            "national_id_input": "",
            "passport_number_input": "P-1234",
            "guardians-TOTAL_FORMS": "0",
            "guardians-INITIAL_FORMS": "0",
            "student_records-TOTAL_FORMS": "0",
            "student_records-INITIAL_FORMS": "0",
        },
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    person = Person.objects.get(pk=person.pk)
    assert person.family_name == "After"
    assert person.name_variants == {"ko": "김"}
    assert person.national_id_encrypted == "TEST-000111"
    assert person.passport_number_encrypted == "P-1234"


def test_lists_second_major_applications_to_the_target_program(manager: Any) -> None:
    assert (
        signed_in(manager)
        .get(f"/admin/person/additionalprogramrequest/?status__exact={AdditionalProgramRequestStatus.APPROVED.value}")
        .status_code
        == 200
    )


@pytest.mark.parametrize(("locale", "texts"), [("ko", ["학생과 교직원", "학적 상태"]), ("zh-hans", ["学籍"])])
def test_renders_the_student_record_list_in_korean_and_chinese(manager: User, locale: str, texts: list[str]) -> None:
    manager.locale = locale
    manager.save(update_fields=["locale"])

    page = signed_in(manager).get("/admin/person/studentrecord/").content.decode()

    for text in texts:
        assert text in page
