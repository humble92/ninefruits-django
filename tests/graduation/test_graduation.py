"""Graduation and reports (original ``tests/Feature/Graduation/GraduationTest.php``): the degree
audit (categories with subcategories, required courses with equivalents, course groups, totals,
waivers with two people, the GPA minimum), stored audits and graduation with a degree number,
visibility at the database level and in the screens, and the standard reports from the reporting
views and as CSV. Actions run with the acting user's database context (row level security
applies, like a real request)."""

from __future__ import annotations

from datetime import date
from io import StringIO
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command

from ninefruits.audit.models import ActivityLog, SecurityEvent
from ninefruits.audit.security_events import SecurityEventType
from ninefruits.curriculum.enums import ProgramRole
from ninefruits.curriculum.models import CourseEquivalency
from ninefruits.graduation.actions import GraduateStudents, RunDegreeAudits, WaiveRequirement
from ninefruits.graduation.enums import WaiverStatus
from ninefruits.graduation.models import DegreeAudit as StoredAudit
from ninefruits.graduation.models import DegreeRequirementWaiver
from ninefruits.graduation.services import DegreeAudit
from ninefruits.person.enums import StudentStatus
from ninefruits.reporting.services import ReportCatalog
from ninefruits.security.enums import Permission
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory

from .conftest import act, pass_course, set_minimum_gpa, signed_in

pytestmark = pytest.mark.django_db

WAIVERS_URL = "/admin/graduation/degreerequirementwaiver/"
AUDITS_URL = "/admin/graduation/degreeaudit/"


def message_of(error: ValidationError) -> str:
    return " ".join(str(message) for message in error.messages)


def raises_message(message: str, call: Any) -> None:
    with pytest.raises(ValidationError) as caught:
        call()
    assert message in message_of(caught.value)


def primary(world: dict[str, Any]) -> Any:
    record = world["record"]
    return DegreeAudit().evaluate(record, record.program, ProgramRole.PRIMARY)


def test_judges_categories_with_subcategories_required_courses_with_equivalents_course_groups_and_totals(
    world: dict[str, Any],
) -> None:
    record, term, courses, staff = world["record"], world["term"], world["courses"], world["staff"]
    result = primary(world)
    assert result.is_satisfied() is False
    assert result.earned_credits == 0
    assert len(result.requirements) == 3
    assert "Total credits 0 of 12 required." in result.issues

    pass_course(record, term, courses["GEN101"])
    pass_course(record, term, courses["GEN102"])
    # The old course counts for MAJ201 through an equivalency valid when it was taken.
    CourseEquivalency.objects.create(
        course=courses["OLD201"],
        equivalent_course=courses["MAJ201"],
        is_mutual=True,
        effective_start_date=date(2020, 1, 1),
    )
    pass_course(record, term, courses["OLD201"])
    pass_course(record, term, courses["MAJ202"])
    pass_course(record, term, courses["MAJ203"], "F")

    result = primary(world)
    general, required, group = result.requirements
    assert general.achieved_credits == 6
    assert general.is_satisfied is True
    assert required.is_satisfied is True
    assert required.courses[0]["code"] == "OLD201"
    assert group.achieved_courses == 1
    assert group.is_satisfied is False
    assert result.earned_credits == 12
    assert result.is_satisfied() is False

    # A waiver satisfies the group once another person approves it; the GPA minimum then blocks
    # until grades are good enough.
    waive = WaiveRequirement()
    waiver = act(world, staff, lambda: waive.request(record, world["group_line"], "Transfer credit from abroad", staff))
    raises_message(
        "A pending or approved waiver already exists for this requirement.",
        lambda: act(world, staff, lambda: waive.request(record, world["group_line"], "Again", staff)),
    )
    raises_message("You cannot decide your own waiver request.", lambda: waive.approve(waiver, staff))
    assert primary(world).requirements[2].is_waived is False
    approver = UserFactory(
        permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.GRADUATION_PROCESS, Permission.STUDENT_RECORDS_VIEW]
    )
    raises_message("Only an approved waiver can be lifted.", lambda: waive.lift(waiver, approver, "x"))
    act(world, approver, lambda: waive.approve(waiver, approver, "Checked"))
    waiver.refresh_from_db()
    assert waiver.status == WaiverStatus.APPROVED
    set_minimum_gpa(None)
    assert primary(world).is_satisfied() is True

    set_minimum_gpa(3.0)
    result = primary(world)
    assert len(result.issues) == 1
    assert "3" in result.issues[0]

    # Lifting takes the waiver out of the audit again; the admin screens decide and lift.
    act(world, approver, lambda: waive.lift(waiver, approver, "Transcript turned out incomplete"))
    waiver.refresh_from_db()
    assert waiver.status == WaiverStatus.LIFTED
    assert primary(world).requirements[2].is_satisfied is False
    second = act(world, staff, lambda: waive.request(record, world["group_line"], "Second look", staff))

    approver_client = signed_in(approver)
    listing = approver_client.get(WAIVERS_URL)
    assert listing.status_code == 200
    assert record.student_number in listing.content.decode()
    response = approver_client.post(f"{WAIVERS_URL}{second.pk}/approve/", {"note": "OK"})
    assert response.status_code == 302
    second.refresh_from_db()
    assert second.status == WaiverStatus.APPROVED
    assert ActivityLog.objects.filter(event="graduation.waiver_approved").count() == 2

    staff_client = signed_in(staff)
    assert staff_client.get(f"{WAIVERS_URL}?status=approved").status_code == 200
    # Approving is not offered for an approved waiver.
    assert staff_client.get(f"{WAIVERS_URL}{second.pk}/approve/").status_code == 403
    assert staff_client.post(f"{WAIVERS_URL}{second.pk}/lift/", {"reason": "Error"}).status_code == 302
    second.refresh_from_db()
    assert second.status == WaiverStatus.LIFTED
    response = staff_client.post(
        f"/admin/person/studentrecord/{record.pk}/waive-requirement/",
        {"requirement": world["group_line"].pk, "reason": "From the screen"},
    )
    assert response.status_code == 302
    assert DegreeRequirementWaiver.objects.filter(status=WaiverStatus.PENDING).count() == 1

    other = StudentRecordFactory(catalog_year=2010)
    assert DegreeAudit().evaluate(other, other.program, ProgramRole.PRIMARY).issues[0] == (
        "No graduation requirements are defined for catalog year 2010."
    )


def test_stores_audits_graduates_from_the_latest_satisfied_one_and_issues_a_degree_number(
    world: dict[str, Any],
) -> None:
    record, term, courses, staff = world["record"], world["term"], world["courses"], world["staff"]
    graduate = GraduateStudents()
    on = date(2026, 2, 20)
    raises_message(
        "No stored degree audit: run the audit first.",
        lambda: act(world, staff, lambda: graduate.handle(record, on, staff, "Spring commencement")),
    )

    out = StringIO()
    code = call_command(
        "degree_audit_run", student_number=record.student_number, actor=staff.email, stdout=out, stderr=StringIO()
    )
    assert code == 0
    assert "1 student(s) audited, 0 satisfied." in out.getvalue()
    assert StoredAudit.objects.count() == 1
    raises_message(
        "The latest degree audit is not satisfied.",
        lambda: act(world, staff, lambda: graduate.handle(record, on, staff, "Spring commencement")),
    )

    for code_ in ("GEN101", "GEN102", "MAJ201", "MAJ202", "MAJ203"):
        pass_course(record, term, courses[code_])
    out = StringIO()
    call_command("degree_audit_run", term=term.code, min_year_level=4, actor=staff.email, stdout=out)
    assert "1 student(s) audited, 1 satisfied." in out.getvalue()
    assert call_command("degree_audit_run", term="NOPE", stdout=StringIO(), stderr=StringIO()) == 1
    assert StoredAudit.objects.newest_per_student().count() == 1
    assert StoredAudit.objects.count() == 2
    run = ActivityLog.objects.filter(event="graduation.audits_run").latest("id")
    assert run.properties == {"students": 1, "satisfied": 1}

    clerk = UserFactory(permissions=[Permission.GRADUATION_AUDIT, Permission.STUDENT_RECORDS_VIEW])
    with pytest.raises(PermissionDenied):
        graduate.handle(record, on, clerk, "x")

    act(world, staff, lambda: graduate.handle(record, on, staff, "Spring commencement"))
    record.refresh_from_db()
    assert record.status == StudentStatus.GRADUATED
    assert record.degree_number == f"{record.program.code}-2026-00001"
    assert record.graduation_date == on
    assert ActivityLog.objects.filter(event="graduation.processed").exists()
    raises_message(
        "Only an enrolled student can graduate.",
        lambda: act(world, staff, lambda: graduate.handle(record, on, staff, "Again")),
    )

    second = StudentRecordFactory(program=record.program, catalog_year=2024)
    for code_ in ("GEN101", "GEN102", "MAJ201", "MAJ202", "MAJ203"):
        pass_course(second, term, courses[code_])
    act(world, staff, lambda: RunDegreeAudits().for_record(second, staff))
    unaudited = StudentRecordFactory()
    summary = act(world, staff, lambda: graduate.batch([second, unaudited], on, staff, "Batch"))
    assert summary["graduated"] == 1
    assert len(summary["errors"]) == 1
    second.refresh_from_db()
    assert second.degree_number == f"{record.program.code}-2026-00002"


def test_shows_audits_to_staff_and_the_student_at_the_database_level_and_in_the_screens(
    world: dict[str, Any],
) -> None:
    record, term, courses, staff, student = (
        world["record"],
        world["term"],
        world["courses"],
        world["staff"],
        world["student"],
    )
    pass_course(record, term, courses["GEN101"])
    act(world, staff, lambda: RunDegreeAudits().for_record(record, staff))
    stranger = UserFactory(person=StudentRecordFactory().person)

    with world["as_user"](student):
        assert StoredAudit.objects.count() == 1
        assert StoredAudit.objects.update(is_satisfied=True) == 0
        assert StoredAudit.objects.visible_to(student).count() == 1
    with world["as_user"](stranger):
        assert StoredAudit.objects.count() == 0
        assert StoredAudit.objects.visible_to(stranger).count() == 0
    with world["as_user"](staff):
        assert StoredAudit.objects.count() == 1
        assert StoredAudit.objects.visible_to(staff).count() == 1

    client = signed_in(staff)
    listing = client.get(AUDITS_URL)
    assert listing.status_code == 200
    assert record.student_number in listing.content.decode()
    assert client.get("/admin/settings/graduation/").status_code == 200
    audit = StoredAudit.objects.get()
    assert client.get(f"{AUDITS_URL}{audit.pk}/open/").status_code == 200
    assert client.post(f"{AUDITS_URL}{audit.pk}/rerun/", {}).status_code == 302
    assert StoredAudit.objects.count() == 2
    page = client.get(f"/admin/person/studentrecord/{record.pk}/degree-audit/")
    assert page.status_code == 200
    assert "GEN101" in page.content.decode()
    assert client.post(f"/admin/person/studentrecord/{record.pk}/degree-audit/").status_code == 302
    assert StoredAudit.objects.count() == 3

    portal = signed_in(student).get("/portal/graduation/")
    assert portal.status_code == 200
    content = portal.content.decode()
    assert "Graduation requirements" in content
    assert "GEN101" in content


def test_serves_the_standard_reports_from_the_reporting_views_and_as_csv(world: dict[str, Any]) -> None:
    record, term, courses, staff, student = (
        world["record"],
        world["term"],
        world["courses"],
        world["staff"],
        world["student"],
    )
    pass_course(record, term, courses["GEN101"])
    act(world, staff, lambda: RunDegreeAudits().for_record(record, staff))
    catalog = ReportCatalog()

    assert record.student_number in [row["student_number"] for row in catalog.rows("students", {"status": "enrolled"})]
    assert sum(row["students"] for row in catalog.rows("headcount", {})) > 0
    assert catalog.rows("section_enrollments", {"term": term.pk})[0]["enrolled"] == 1
    assert record.student_number not in [
        row["student_number"] for row in catalog.rows("not_registered", {"term": term.pk})
    ]
    assert record.student_number in [
        row["student_number"] for row in catalog.rows("graduation_candidates", {"satisfied": "no"})
    ]
    assert catalog.rows("status_changes", {"date_from": "2000-01-01"}) == []

    client = signed_in(staff)
    response = client.get("/reports/students.csv", {"status": "enrolled"})
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=UTF-8"
    assert record.student_number in response.content.decode("utf-8")
    assert ActivityLog.objects.filter(event="reports.exported").exists()
    assert SecurityEvent.objects.filter(type=SecurityEventType.DATA_EXPORTED, user_id=staff.pk).exists()
    assert client.get("/reports/nope.csv").status_code == 404
    assert signed_in(student).get("/reports/students.csv").status_code == 403

    assert client.get("/admin/reports/").status_code == 200
    page = client.get("/admin/reports/", {"report": "section_enrollments", "term": term.pk})
    assert page.status_code == 200
    assert "GEN101" in page.content.decode()

    # The views apply the reader's row level security: the student sees only themselves.
    with world["as_user"](student):
        assert [row["student_number"] for row in catalog.rows("students", {})] == [record.student_number]
