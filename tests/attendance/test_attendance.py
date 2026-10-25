"""Class meetings and attendance (original ``tests/Feature/Attendance/AttendanceTest.php``):
idempotent generation and the command, added and cancelled meetings, attendance entry with only
changes written and audited, the totals, row level security for the instructor and the student,
the roster CSV (with the spreadsheet formula guard) and attendance sheet for the instructor and
staff only, and the portal pages and the admin class meetings tab."""

from __future__ import annotations

import csv
import io
import re
from datetime import time, timedelta

import httpx
import pytest
import respx
from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.utils import timezone

from ninefruits.attendance.actions import GenerateClassMeetings, ManageClassMeetings, RecordAttendance
from ninefruits.attendance.enums import AttendanceStatus, ClassMeetingStatus
from ninefruits.attendance.models import AttendanceRecord, ClassMeeting
from ninefruits.attendance.services import AttendanceSummary, SectionRoster, spreadsheet_cell
from ninefruits.audit.models import ActivityLog
from ninefruits.core.db import session_context
from ninefruits.person.models import Person, StudentRecord
from tests.factories.person import InstructorFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory

from .conftest import Classroom, signed_in

pytestmark = pytest.mark.django_db

CONVERT = f"{settings.GOTENBERG_URL.rstrip('/')}/forms/chromium/convert/html"


def first_meeting(classroom: Classroom) -> ClassMeeting:
    return ClassMeeting.objects.filter(section=classroom.section).order_by("meeting_date").first()


def run(*args: str) -> tuple[int, str]:
    out = io.StringIO()
    code = call_command("attendance_generate_sessions", *args, stdout=out, stderr=out)
    return code, out.getvalue()


def test_generates_meetings_from_the_weekly_meeting_times_idempotently(classroom: Classroom) -> None:
    generate = GenerateClassMeetings()
    assert generate.for_section(classroom.section, classroom.teacher) == 16
    assert generate.for_section(classroom.section, classroom.teacher) == 0
    assert ClassMeeting.objects.filter(section=classroom.section).count() == 16
    assert first_meeting(classroom).meeting_date.isoweekday() == 1
    assert ActivityLog.objects.filter(event="attendance.meetings_generated").count() == 1

    assert run("NOPE")[0] == 1
    code, output = run(classroom.term.code, "--dry-run")
    assert code == 0 and "1 section(s) would be processed." in output
    code, output = run(classroom.term.code)
    assert code == 0 and "1 section(s): 0 meeting(s) created." in output
    code, output = run(classroom.term.code, f"--section={classroom.section.label()}")
    assert code == 0 and "1 section(s): 0 meeting(s) created." in output

    # Adding and cancelling meetings.
    manage = ManageClassMeetings()
    today = timezone.localdate()
    added = manage.add(classroom.section, today + timedelta(days=2), "14:00", "15:50", classroom.teacher)
    assert added.section_meeting_id is None
    with pytest.raises(ValidationError, match=re.escape("A meeting at that date and time already exists.")):
        manage.add(classroom.section, today + timedelta(days=2), "14:00", "15:50", classroom.teacher)
    with pytest.raises(ValidationError, match=re.escape("The date is outside the session.")):
        manage.add(classroom.section, today + timedelta(days=730), "14:00", "15:50", classroom.teacher)
    with pytest.raises(ValidationError, match=re.escape("The end time must be after the start time.")):
        manage.add(classroom.section, today, "15:00", "14:00", classroom.teacher)
    with pytest.raises(PermissionDenied):
        manage.add(classroom.section, today, "14:00", "15:00", classroom.student)

    first = first_meeting(classroom)
    manage.cancel(first, classroom.staff, "Public holiday")
    first.refresh_from_db()
    assert first.status == ClassMeetingStatus.CANCELLED
    assert first.cancel_reason == "Public holiday"
    with pytest.raises(ValidationError, match=re.escape("This meeting is already cancelled.")):
        manage.cancel(first, classroom.staff, "Again")
    with pytest.raises(ValidationError, match=re.escape("This meeting is cancelled.")):
        RecordAttendance().save(first, {classroom.enrollments[0].pk: "present"}, classroom.teacher)
    manage.restore(first, classroom.teacher)
    first.refresh_from_db()
    assert first.status == ClassMeetingStatus.SCHEDULED
    assert first.cancel_reason is None


def test_cancelling_needs_a_reason(classroom: Classroom) -> None:
    GenerateClassMeetings().for_section(classroom.section)
    with pytest.raises(ValidationError, match=re.escape("Enter a reason.")):
        ManageClassMeetings().cancel(first_meeting(classroom), classroom.teacher, "  ")


def test_records_attendance_per_meeting_and_totals_it_with_the_audit_trail(classroom: Classroom) -> None:
    GenerateClassMeetings().for_section(classroom.section)
    first, second = list(ClassMeeting.objects.filter(section=classroom.section).order_by("meeting_date")[:2])
    a, b, c = classroom.enrollments
    record = RecordAttendance()

    assert record.save(first, {a.pk: "present", b.pk: "late", c.pk: "absent"}, classroom.teacher, {b.pk: "Bus"}) == 3
    late = AttendanceRecord.objects.get(enrollment=b)
    assert late.status == AttendanceStatus.LATE and late.note == "Bus"
    assert late.recorded_by_id == classroom.teacher.pk
    # Saving the same statuses writes nothing; a change replaces and is audited with the previous value.
    assert record.save(first, {a.pk: "present", b.pk: "late", c.pk: "absent"}, classroom.teacher, {b.pk: "Bus"}) == 0
    record.save(first, {c.pk: "excused"}, classroom.teacher)
    entry = ActivityLog.objects.filter(event="attendance.recorded").order_by("-id").first()
    assert entry.properties["changes"][str(c.pk)] == ["absent", "excused"]
    assert entry.properties["section_id"] == classroom.section.pk
    record.save(second, {a.pk: "present", b.pk: "absent", c.pk: None}, classroom.staff)

    summary = AttendanceSummary().for_section(classroom.section, SectionRoster().enrollments(classroom.section))
    assert summary["held"] == 16
    assert summary["students"][a.pk]["present"] == 2
    assert summary["students"][a.pk]["missing"] == 14
    assert summary["students"][a.pk]["rate"] == 12.5
    assert summary["students"][b.pk]["late"] == 1 and summary["students"][b.pk]["absent"] == 1
    assert summary["students"][c.pk]["excused"] == 1
    assert summary["students"][c.pk]["absent"] == 0
    assert summary["students"][c.pk]["missing"] == 15

    # Clearing a status deletes the record and audits it.
    record.save(second, {b.pk: None}, classroom.teacher)
    assert not AttendanceRecord.objects.filter(class_meeting=second, enrollment=b).exists()

    future = ManageClassMeetings().add(
        classroom.section, timezone.localdate() + timedelta(days=1), "09:00", "10:00", classroom.teacher
    )
    with pytest.raises(ValidationError, match=re.escape("Attendance can be entered from the day of the meeting.")):
        record.save(future, {a.pk: "present"}, classroom.teacher)
    other = EnrollmentFactory()
    with pytest.raises(ValidationError, match=re.escape("A student is not enrolled in this section.")):
        record.save(first, {other.pk: "present"}, classroom.teacher)
    with pytest.raises(PermissionDenied):
        record.save(first, {a.pk: "present"}, classroom.student)
    with pytest.raises(ValidationError, match=re.escape("Unknown attendance status.")):
        record.save(first, {a.pk: "nope"}, classroom.teacher)


def test_summary_rate_rounds_half_up_and_is_empty_without_held_meetings() -> None:
    summary = AttendanceSummary()
    assert summary.counts(["present", "late", "excused"], 0)["rate"] is None
    # 1 / 8 = 12.5 %, 1 / 6 = 16.666..., 1 / 16 = 6.25 -> 6.3 (PHP round).
    assert summary.counts(["present"], 8)["rate"] == 12.5
    assert summary.counts(["late"], 6)["rate"] == 16.7
    assert summary.counts(["excused"], 16)["rate"] == 6.3
    assert summary.counts(["absent", "absent"], 2) == {
        "present": 0,
        "late": 0,
        "absent": 2,
        "excused": 0,
        "missing": 0,
        "rate": 0.0,
    }
    assert AttendanceSummary.is_counted_present("excused") and not AttendanceSummary.is_counted_present("absent")


def test_lets_the_instructor_see_the_roster_and_records_at_the_database_level(
    classroom: Classroom, without_baseline: None
) -> None:
    context = session_context()
    context.use_baseline({"app.actor": "system:test"})
    GenerateClassMeetings().for_section(classroom.section)
    meeting = first_meeting(classroom)
    a, b, _c = classroom.enrollments
    RecordAttendance().save(meeting, {a.pk: "present", b.pk: "absent"}, classroom.teacher)
    stranger = UserFactory(person=InstructorFactory().person)
    context.use_baseline({})

    context.for_user(classroom.teacher.pk)
    assert StudentRecord.objects.count() == 3
    assert Person.objects.filter(student_records__isnull=False).distinct().count() == 3
    assert AttendanceRecord.objects.count() == 2
    assert ClassMeeting.objects.count() == 16
    assert AttendanceRecord.objects.filter(enrollment=a).update(status="late") == 1
    assert a.student_record.is_visible_to(classroom.teacher)
    # The application scopes give the same answers.
    assert StudentRecord.objects.visible_to(classroom.teacher).count() == 3
    assert AttendanceRecord.objects.visible_to(classroom.teacher).count() == 2
    context.reset()

    context.for_user(classroom.student.pk)
    assert AttendanceRecord.objects.count() == 1
    assert AttendanceRecord.objects.update(status="present") == 0
    assert StudentRecord.objects.count() == 1
    assert AttendanceRecord.objects.visible_to(classroom.student).count() == 1
    context.reset()

    context.for_user(stranger.pk)
    assert AttendanceRecord.objects.count() == 0
    assert StudentRecord.objects.count() == 0
    assert not a.student_record.is_visible_to(stranger)
    assert AttendanceRecord.objects.visible_to(stranger).count() == 0
    context.reset()


@respx.mock
def test_serves_the_roster_csv_and_the_attendance_sheet_to_the_instructor_and_staff_only(
    classroom: Classroom,
) -> None:
    route = respx.post(CONVERT).mock(return_value=httpx.Response(200, content=b"%PDF-1.7 fake"))
    GenerateClassMeetings().for_section(classroom.section)
    RecordAttendance().save(first_meeting(classroom), {classroom.enrollments[0].pk: "present"}, classroom.teacher)

    response = signed_in(classroom.teacher).get(f"/sections/{classroom.section.pk}/roster.csv")
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=UTF-8"
    assert response["Content-Disposition"] == f'attachment; filename="{classroom.section.label()}-roster.csv"'
    assert response["Cache-Control"] == "private, no-store"
    content = response.content
    assert content.startswith(b"\xef\xbb\xbf")
    assert classroom.enrollments[0].student_record.student_number in content.decode()
    assert ActivityLog.objects.filter(event="attendance.roster_exported").exists()

    sheet = signed_in(classroom.staff).get(f"/sections/{classroom.section.pk}/attendance-sheet")
    assert sheet.status_code == 200
    assert sheet["Content-Type"] == "application/pdf"
    assert sheet.content == b"%PDF-1.7 fake"
    assert ActivityLog.objects.filter(event="attendance.sheet_exported").exists()
    assert b'name="landscape"\r\n\r\ntrue' in route.calls.last.request.content
    # The instructor's sheet has the students and the recorded mark.
    assert signed_in(classroom.teacher).get(f"/sections/{classroom.section.pk}/attendance-sheet").status_code == 200
    sent = route.calls.last.request.content.decode()
    assert classroom.enrollments[0].student_record.student_number in sent
    assert "<td>O</td>" in sent

    student = signed_in(classroom.student)
    assert student.get(f"/sections/{classroom.section.pk}/roster.csv").status_code == 403
    assert student.get(f"/sections/{classroom.section.pk}/attendance-sheet").status_code == 403


def test_roster_csv_neutralises_spreadsheet_formulas(classroom: Classroom) -> None:
    """Original ``ReportCatalog::cell`` (``HardeningTest``), used by the roster CSV."""
    assert spreadsheet_cell("=1+1") == "'=1+1"
    assert spreadsheet_cell("+123") == "'+123"
    assert spreadsheet_cell("-5") == "'-5"
    assert spreadsheet_cell("@x") == "'@x"
    assert spreadsheet_cell("\tx") == "'\tx"
    assert spreadsheet_cell("plain") == "plain"
    assert spreadsheet_cell(None) == ""
    assert spreadsheet_cell(True) == "Y"

    person = classroom.enrollments[1].student_record.person
    person.family_name = '=HYPERLINK("http://example.test")'
    person.given_name = "=1+1"
    person.save()
    rows = list(csv.reader(io.StringIO(SectionRoster().csv(classroom.section).lstrip("﻿"))))
    assert rows[0][0] == "Student number"
    assert len(rows) == 4
    names = [row[1] for row in rows[1:]]
    assert any(name.startswith("'=") for name in names)
    assert not any(name.startswith("=") for name in names)


def test_works_from_the_portal_pages(classroom: Classroom) -> None:
    section = classroom.section
    url = f"/portal/sections/{section.pk}/attendance/"
    assert signed_in(classroom.student).get(url).status_code == 403
    teaching = signed_in(classroom.teacher).get(f"/portal/teaching/?term={classroom.term.pk}").content.decode()
    assert url in teaching

    teacher = signed_in(classroom.teacher)
    page = teacher.get(url).content.decode()
    assert "No class meetings yet. Generate them from the weekly meeting times." in page
    response = teacher.post(url, {"action": "generate"}, follow=True)
    assert "16 meeting(s) created." in response.content.decode()

    meeting = first_meeting(classroom)
    entry = teacher.get(f"{url}?meeting={meeting.pk}").content.decode()
    assert "Save attendance" in entry
    a, b, c = classroom.enrollments
    # "All present" fills the form without saving.
    marked = teacher.post(
        f"{url}?meeting={meeting.pk}", {"action": "mark_all:present", "meeting": meeting.pk}
    ).content.decode()
    assert marked.count('value="present" checked') == 3
    assert not AttendanceRecord.objects.filter(class_meeting=meeting).exists()
    response = teacher.post(
        f"{url}?meeting={meeting.pk}",
        {
            "action": "save",
            "meeting": meeting.pk,
            f"status-{a.pk}": "present",
            f"status-{b.pk}": "absent",
            f"status-{c.pk}": "present",
            f"note-{b.pk}": "Sick",
        },
        follow=True,
    )
    assert "Attendance saved." in response.content.decode()
    assert AttendanceRecord.objects.filter(class_meeting=meeting).count() == 3
    absent = AttendanceRecord.objects.get(enrollment=b)
    assert absent.status == AttendanceStatus.ABSENT and absent.note == "Sick"

    # Errors show the page again with the message.
    future = ManageClassMeetings().add(
        section, timezone.localdate() + timedelta(days=1), "09:00", "10:00", classroom.teacher
    )
    failed = teacher.post(
        f"{url}?meeting={future.pk}", {"action": "save", "meeting": future.pk, f"status-{a.pk}": "present"}
    ).content.decode()
    assert "Attendance can be entered from the day of the meeting." in failed

    response = teacher.post(
        url, {"action": f"cancel_meeting:{meeting.pk}", f"reason-{meeting.pk}": "Snow day"}, follow=True
    )
    assert "Meeting cancelled." in response.content.decode()
    meeting.refresh_from_db()
    assert meeting.status == ClassMeetingStatus.CANCELLED and meeting.cancel_reason == "Snow day"
    response = teacher.post(url, {"action": f"restore_meeting:{meeting.pk}"}, follow=True)
    assert "Meeting restored." in response.content.decode()

    added = teacher.post(
        url,
        {
            "action": "add_meeting",
            "meeting_date": (timezone.localdate() + timedelta(days=3)).isoformat(),
            "start_time": "18:00",
            "end_time": "19:30",
        },
        follow=True,
    ).content.decode()
    assert "Meeting added." in added
    assert ClassMeeting.objects.filter(section=section, start_time=time(18, 0)).exists()
    wrong = teacher.post(
        url,
        {
            "action": "add_meeting",
            "meeting_date": timezone.localdate().isoformat(),
            "start_time": "19:00",
            "end_time": "18:00",
        },
    ).content.decode()
    assert "The end time must be after the start time." in wrong

    # Staff who only view sections see the page but cannot change it.
    viewer = UserFactory(permissions=["sections.view"])
    viewer_client = signed_in(viewer)
    assert viewer_client.get(url).status_code == 200
    refused = viewer_client.post(url, {"action": "generate"}).content.decode()
    assert "Only the section&#x27;s instructors and the staff who manage it can do this." in refused

    my = signed_in(classroom.student).get("/portal/attendance/").content.decode()
    assert section.label() in my
    assert "Present 1" in my
    assert signed_in(classroom.student).get(f"/portal/attendance/?term={classroom.term.pk}").status_code == 200


def test_my_attendance_counts_held_meetings_only(classroom: Classroom) -> None:
    GenerateClassMeetings().for_section(classroom.section)
    a = classroom.enrollments[0]
    meeting = first_meeting(classroom)
    RecordAttendance().save(meeting, {a.pk: "late"}, classroom.teacher)
    ManageClassMeetings().cancel(
        ClassMeeting.objects.filter(section=classroom.section).order_by("-meeting_date").first(),
        classroom.teacher,
        "Holiday",
    )
    page = signed_in(classroom.student).get("/portal/attendance/").content.decode()
    assert "Present 0" in page and "Late 1" in page
    # 15 held meetings (one cancelled): 1 / 15 = 6.7 %.
    assert "Attendance rate 6.7%" in page
    assert "Not recorded" in page
    # Without a student record: not found.
    assert signed_in(classroom.teacher).get("/portal/attendance/").status_code == 404


def test_admin_class_meetings_tab(classroom: Classroom) -> None:
    staff = signed_in(classroom.staff)
    section_url = f"/admin/offering/section/{classroom.section.pk}/change/"
    page = staff.get(section_url).content.decode()
    assert "data-class-meetings" in page
    assert "Class meetings" in page

    response = staff.post(f"/admin/offering/section/{classroom.section.pk}/generate-class-meetings/", {})
    assert response.status_code == 302
    assert ClassMeeting.objects.filter(section=classroom.section).count() == 16
    meeting = first_meeting(classroom)
    page = staff.get(section_url).content.decode()
    assert f'data-meeting="{meeting.pk}"' in page

    cancel = f"/admin/offering/section/{classroom.section.pk}/class-meetings/{meeting.pk}/cancel/"
    assert staff.get(cancel).status_code == 200
    staff.post(cancel, {"reason": "Holiday"})
    meeting.refresh_from_db()
    assert meeting.status == ClassMeetingStatus.CANCELLED
    staff.post(f"/admin/offering/section/{classroom.section.pk}/class-meetings/{meeting.pk}/restore/", {})
    meeting.refresh_from_db()
    assert meeting.status == ClassMeetingStatus.SCHEDULED

    viewer = signed_in(UserFactory(permissions=["admin_panel.access", "sections.view"]))
    assert viewer.get(section_url).status_code == 200
    assert viewer.post(cancel, {"reason": "No"}).status_code == 403
