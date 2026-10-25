"""Attendance screens on the tiny demo (the Phase 10 datasets of the original
``tests/Feature/Admin/AdminPagesTest.php`` style and ``DemoAttendanceSeeder``): the current term's
class meetings and recorded attendance, the seeder running once, the instructor's roster and
attendance page, the student's attendance, the roster CSV and the admin class meetings tab, in
English and Korean."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from django.test import Client

from ninefruits.attendance.enums import AttendanceStatus
from ninefruits.attendance.models import AttendanceRecord, ClassMeeting
from ninefruits.core.db import session_context
from ninefruits.offering.models import Section
from ninefruits.security.models import User
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.demo.attendance import DemoAttendanceSeeder
from ninefruits.setup.seeders.demo.curriculum import DemoCurriculumSeeder
from ninefruits.setup.seeders.demo.grading import DemoGradeHistorySeeder, DemoGradingSeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from ninefruits.setup.seeders.demo.registration import DemoRegistrationSeeder
from tests.factories.security import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def demo(essential_data: None) -> Iterator[None]:
    with use_options(DemoOptions(size="tiny", seed=42)):
        for seeder in (
            DemoAccountSeeder,
            DemoReferenceSeeder,
            DemoPeopleSeeder,
            DemoCurriculumSeeder,
            DemoGradeHistorySeeder,
            DemoRegistrationSeeder,
            DemoGradingSeeder,
            DemoAttendanceSeeder,
        ):
            seeder()()
    yield


def signed_in(user: User, language: str | None = None) -> Client:
    client = Client(headers={"accept-language": language} if language else {})
    client.force_login(user)
    session_context().reset()
    return client


def test_seeds_meetings_and_attendance_once() -> None:
    meetings = ClassMeeting.objects.count()
    records = AttendanceRecord.objects.count()
    assert meetings > 0
    assert records > 0
    statuses = set(AttendanceRecord.objects.values_list("status", flat=True))
    assert AttendanceStatus.PRESENT in statuses
    assert statuses <= set(AttendanceStatus.values)
    assert not AttendanceRecord.objects.exclude(class_meeting__status="scheduled").exists()

    with use_options(DemoOptions(size="tiny", seed=42)):
        DemoAttendanceSeeder()()
    assert ClassMeeting.objects.count() == meetings
    assert AttendanceRecord.objects.count() == records


@pytest.mark.parametrize("language", ["en", "ko"])
def test_renders_the_attendance_pages(language: str) -> None:
    instructor = User.objects.get(email="instructor@demo.test")
    section = (
        Section.objects.taught_by(instructor.person_id).filter(class_meetings__records__isnull=False).distinct().first()
    )
    assert section is not None
    teacher = signed_in(instructor, language)
    page = teacher.get(f"/portal/sections/{section.pk}/attendance/")
    assert page.status_code == 200
    assert "data-roster" in page.content.decode()
    meeting = ClassMeeting.objects.filter(section=section, records__isnull=False).first()
    entry = teacher.get(f"/portal/sections/{section.pk}/attendance/?meeting={meeting.pk}")
    assert entry.status_code == 200 and "data-entry" in entry.content.decode()
    assert teacher.get(f"/sections/{section.pk}/roster.csv").status_code == 200
    assert f"/portal/sections/{section.pk}/attendance/" in teacher.get("/portal/teaching/").content.decode()

    record = AttendanceRecord.objects.filter(class_meeting__section=section).select_related(
        "enrollment__student_record"
    )
    person_id = record.first().enrollment.student_record.person_id
    student = User.objects.filter(person_id=person_id).first() or UserFactory(person_id=person_id)
    mine = signed_in(student, language).get("/portal/attendance/")
    assert mine.status_code == 200
    assert section.label() in mine.content.decode()

    staff = signed_in(UserFactory(permissions=["admin_panel.access", "sections.view", "sections.manage"]), language)
    admin_page = staff.get(f"/admin/offering/section/{section.pk}/change/")
    assert admin_page.status_code == 200
    assert "data-class-meetings" in admin_page.content.decode()
    assert staff.get(f"/admin/offering/section/{section.pk}/generate-class-meetings/").status_code == 200
