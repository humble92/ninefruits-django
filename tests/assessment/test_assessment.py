"""Examinations (original ``tests/Feature/Assessment/AssessmentTest.php``): registration with window
and capacity, pass decisions from scores, pass score and area minimums, locking after publication
and corrections, changing the cut line, visibility to the student, CSV import and publication
commands, the curriculum requirement, and the admin and portal screens. The actions run with the
acting user's database context (row level security applies, like a real request)."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import connection
from django.utils import timezone

from ninefruits.assessment.actions import ChangeSessionPassScore, CorrectAssessmentResult
from ninefruits.assessment.enums import AssessmentRegistrationStatus, CorrectionStatus
from ninefruits.assessment.models import AssessmentRegistration, AssessmentResult, AssessmentSession
from ninefruits.assessment.services import AssessmentPassCheck
from ninefruits.audit.models import ActivityLog
from ninefruits.core.db import session_context
from ninefruits.curriculum.enums import ProgramRole, RequirementKind
from ninefruits.curriculum.models import CurriculumRequirement, CurriculumRequirementSet
from ninefruits.security.enums import Permission
from tests.db.support import database_error
from tests.factories.person import StudentRecordFactory
from tests.factories.security import UserFactory

from .conftest import STAFF_PERMISSIONS, act, scores, set_minimum, signed_in, student_of

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"


def message_of(error: ValidationError) -> str:
    return " ".join(str(message) for message in error.messages)


def raises_message(message: str, call: Any) -> None:
    with pytest.raises(ValidationError) as caught:
        call()
    assert message in message_of(caught.value)


def test_lets_students_register_while_the_window_is_open_and_seats_remain(world: dict[str, Any]) -> None:
    register, session, record, student, staff = (
        world["register"],
        world["session"],
        world["record"],
        world["student"],
        world["staff"],
    )
    registration = act(world, student, lambda: register.register(session, record, student))
    assert registration.status == AssessmentRegistrationStatus.REGISTERED
    assert registration.registered_by_id is None
    assert ActivityLog.objects.filter(event="assessment.registered").count() == 1

    raises_message("Already registered for this session.", lambda: register.register(session, record, student))

    other = StudentRecordFactory()
    act(world, staff, lambda: register.register(session, other, staff, by_staff=True))
    third = StudentRecordFactory()
    third_student = student_of(third)
    # Seats are counted over every registration, not only those the student can see.
    raises_message(
        "This session is full.",
        lambda: act(world, third_student, lambda: register.register(session, third, third_student)),
    )

    # Cancelling frees the seat; registering again reactivates the row.
    act(world, student, lambda: register.cancel(registration, student))
    registration.refresh_from_db()
    assert registration.status == AssessmentRegistrationStatus.CANCELLED
    assert isinstance(
        act(world, staff, lambda: register.register(session, third, staff, by_staff=True)), AssessmentRegistration
    )
    raises_message("This session is full.", lambda: register.register(session, record, student))

    session.registration_closes_at = timezone.now() - timedelta(minutes=1)
    session.capacity = None
    session.save()
    raises_message("Registration for this session is closed.", lambda: register.register(session, record, student))
    again = act(world, staff, lambda: register.register(session, record, staff, by_staff=True))
    assert again.status == AssessmentRegistrationStatus.REGISTERED
    assert again.pk == registration.pk

    # After the session date nobody registers, staff included.
    past = AssessmentSession.objects.create(
        assessment_type=world["english"], held_date=timezone.localdate() - timedelta(days=1)
    )
    raises_message("This session has already been held.", lambda: register.register(past, other, staff, by_staff=True))

    with pytest.raises(PermissionDenied):
        register.register(session, other, student)
    raises_message(
        "Only current students can register.",
        lambda: register.register(session, StudentRecordFactory(graduated=True), staff, by_staff=True),
    )


def test_decides_passes_from_the_scores_the_pass_score_and_the_area_minimums(world: dict[str, Any]) -> None:
    register, results, session, record, staff = (
        world["register"],
        world["results"],
        world["session"],
        world["record"],
        world["staff"],
    )
    registration = act(world, staff, lambda: register.register(session, record, staff, by_staff=True))

    result = act(world, staff, lambda: results.for_registration(registration, scores([20, 15, 15, 10]), None, staff))
    assert str(result.total_score) == "60.0"
    assert result.is_passed is True
    assert result.component_scores.count() == 4

    # Entering again replaces the result.
    again = act(world, staff, lambda: results.for_registration(registration, scores([20, 15, 15, 9]), None, staff))
    assert again.pk == result.pk
    assert str(again.total_score) == "59.0"
    assert again.is_passed is False
    assert AssessmentResult.objects.count() == 1

    with pytest.raises(ValidationError):
        results.for_registration(registration, scores([26, 15, 15, 10]), None, staff)
    with pytest.raises(ValidationError):
        results.for_registration(registration, scores([20, 15, 15, None]), None, staff)

    # An area minimum fails the student whatever the total; the session can raise the pass score.
    set_minimum(world["english"], "WRITING", 10)
    assert results.for_registration(registration, scores([25, 25, 9, 25]), None, staff).is_passed is False
    session.pass_score = Decimal(90)
    session.save()
    assert results.for_registration(registration, scores([25, 20, 20, 20]), None, staff).is_passed is False
    assert results.for_registration(registration, scores([25, 25, 20, 20]), None, staff).is_passed is True

    # Pass/fail kinds need a decision; a score kind without pass score too.
    computer_session = AssessmentSession.objects.create(
        assessment_type=world["computer"], held_date=timezone.localdate()
    )
    computer_registration = register.register(computer_session, record, staff, by_staff=True)
    raises_message(
        "Choose passed or not passed.", lambda: results.for_registration(computer_registration, {}, None, staff)
    )
    assert results.for_registration(computer_registration, {}, True, staff).is_passed is True
    raises_message(
        "A result has been entered; the registration cannot be cancelled.",
        lambda: register.cancel(computer_registration, staff),
    )

    clerk = UserFactory(permissions=[Permission.STUDENT_RECORDS_VIEW])
    with pytest.raises(PermissionDenied):
        results.for_registration(registration, scores([25, 25, 20, 20]), None, clerk)


def test_locks_published_results_and_changes_them_only_through_an_approved_correction(world: dict[str, Any]) -> None:
    register, results, session, record, staff = (
        world["register"],
        world["results"],
        world["session"],
        world["record"],
        world["staff"],
    )
    registration = register.register(session, record, staff, by_staff=True)
    result = act(world, staff, lambda: results.for_registration(registration, scores([20, 20, 20, 20]), None, staff))
    corrections = CorrectAssessmentResult()
    raises_message(
        "This result is not published; enter it directly.",
        lambda: corrections.request(result, {"scores": scores([25, 20, 20, 20])}, "Marking error", staff),
    )

    act(world, staff, lambda: results.publish(session, staff))
    locked = "The results of this session are published: request a correction instead."
    raises_message(locked, lambda: results.for_registration(registration, scores([25, 20, 20, 20]), None, staff))
    raises_message(locked, lambda: results.remove(result, staff, "x"))

    correction = act(
        world, staff, lambda: corrections.request(result, {"scores": scores([25, 20, 20, 20])}, "Marking error", staff)
    )
    assert correction.previous["total"] == "80.0"
    assert correction.status == CorrectionStatus.PENDING
    raises_message(
        "A correction request is already pending for this result.",
        lambda: corrections.request(result, {"scores": scores([25, 20, 20, 20])}, "Again", staff),
    )
    raises_message("You cannot decide your own correction request.", lambda: corrections.approve(correction, staff))
    recorder = UserFactory(permissions=[Permission.ASSESSMENTS_RECORD, Permission.STUDENT_RECORDS_VIEW])
    with pytest.raises(PermissionDenied):
        corrections.approve(correction, recorder)

    approver = UserFactory(permissions=STAFF_PERMISSIONS)
    act(world, approver, lambda: corrections.approve(correction, approver, "Checked the paper"))
    result.refresh_from_db()
    correction.refresh_from_db()
    assert str(result.total_score) == "85.0"
    assert correction.status == CorrectionStatus.APPROVED
    assert ActivityLog.objects.filter(event="assessment.result_corrected").exists()
    with pytest.raises(ValidationError):
        corrections.approve(correction, approver)

    second = corrections.request(result, {"scores": scores([25, 25, 20, 20])}, "Second look", staff)
    corrections.reject(second, approver, "No grounds")
    second.refresh_from_db()
    result.refresh_from_db()
    assert second.status == CorrectionStatus.REJECTED
    assert str(result.total_score) == "85.0"

    third = corrections.request(result, {"scores": scores([25, 25, 20, 20])}, "Typo", staff)
    corrections.cancel(third, staff)
    third.refresh_from_db()
    assert third.status == CorrectionStatus.CANCELLED

    assert signed_in(approver).get("/admin/assessment/assessmentresultcorrection/?status=all").status_code == 200
    # The registrants tab: no result entry after publication, a correction request instead.
    content = signed_in(staff).get(f"/admin/assessment/assessmentsession/{session.pk}/change/").content.decode()
    assert f"/registrations/{registration.pk}/result/" not in content
    assert f"/registrations/{registration.pk}/correct/" in content


def test_fails_a_student_below_an_area_minimum_whatever_the_total_and_passes_one_exactly_at_it(
    world: dict[str, Any],
) -> None:
    register, results, staff = world["register"], world["results"], world["staff"]
    # Writing requires at least 10 of 25; the kind's pass score stays 60.
    set_minimum(world["english"], "WRITING", 10)
    registration = register.register(world["session"], world["record"], staff, by_staff=True)

    below = results.for_registration(registration, scores([25, 25, 9, 25]), None, staff)
    assert (str(below.total_score), below.is_passed) == ("84.0", False)
    at = results.for_registration(registration, scores([25, 25, 10, 25]), None, staff)
    assert (str(at.total_score), at.is_passed) == ("85.0", True)
    low = results.for_registration(registration, scores([10, 10, 10, 10]), None, staff)
    assert (str(low.total_score), low.is_passed) == ("40.0", False)

    # Without area minimums the same 84 passes: the profile seeds none, so only the total applies.
    set_minimum(world["english"], "WRITING", None)
    assert results.for_registration(registration, scores([25, 25, 9, 25]), None, staff).is_passed is True


def test_changes_the_cut_line_before_publication_judging_entered_results_again_and_never_after(
    world: dict[str, Any],
) -> None:
    register, results, session, staff = world["register"], world["results"], world["session"], world["staff"]
    session.capacity = None
    session.save()
    a, b, c = StudentRecordFactory(), StudentRecordFactory(), StudentRecordFactory()
    change = ChangeSessionPassScore()
    registrations = [register.register(session, record, staff, by_staff=True) for record in (a, b, c)]
    results.for_registration(registrations[0], scores([15, 15, 15, 15]), None, staff)  # 60: passes at 60
    results.for_registration(registrations[1], scores([14, 14, 14, 13]), None, staff)  # 55: fails at 60
    results.for_registration(registrations[2], scores([10, 10, 10, 10]), None, staff)  # 40

    summary = act(world, staff, lambda: change.handle(session, 55, staff, "Hard paper, agreed in the meeting"))
    assert summary == {"rejudged": 3, "now_passed": [b.student_number], "now_failed": []}
    assert AssessmentResult.objects.get(student_record=b).is_passed is True
    assert ActivityLog.objects.get(event="assessment.pass_score_changed").properties["to"] == 55

    # Lowering it further: 40 still fails at 50, and a new area minimum (grammar 14) fails the 55
    # whatever the cut line.
    set_minimum(world["english"], "GRAMMAR", 14)
    summary = change.handle(session, 50, staff)
    assert summary["now_failed"] == [b.student_number]
    assert summary["now_passed"] == []
    # Even at 40 the grammar minimum keeps both below it failing; only the clean 60 passes.
    summary = change.handle(session, 40, staff)
    assert (summary["now_passed"], summary["now_failed"]) == ([], [])
    assert AssessmentResult.objects.filter(is_passed=True).count() == 1

    clerk = UserFactory(permissions=[Permission.ASSESSMENTS_RECORD, Permission.STUDENT_RECORDS_VIEW])
    with pytest.raises(PermissionDenied):
        change.handle(session, 60, clerk)

    results.publish(session, staff)
    raises_message(
        "The results are published: the pass score cannot change. Use correction requests.",
        lambda: change.handle(session, 60, staff),
    )

    # The session form keeps the pass score read only after publication.
    from django.contrib import admin
    from django.test import RequestFactory

    request = RequestFactory().get("/")
    request.user = staff
    session.refresh_from_db()
    assert "pass_score" in admin.site._registry[AssessmentSession].get_readonly_fields(request, session)


def test_shows_results_to_the_student_only_once_published_and_external_results_at_once(
    world: dict[str, Any], without_baseline: None
) -> None:
    register, results, session, record, staff, student = (
        world["register"],
        world["results"],
        world["session"],
        world["record"],
        world["staff"],
        world["student"],
    )
    context = session_context()
    context.for_system("test")
    registration = register.register(session, record, staff, by_staff=True)
    results.for_registration(registration, scores([20, 20, 20, 20]), None, staff)
    stranger = student_of(StudentRecordFactory())

    context.for_user(student.pk)
    assert AssessmentResult.objects.count() == 0
    assert AssessmentRegistration.objects.count() == 1
    context.for_user(stranger.pk)
    assert AssessmentRegistration.objects.count() == 0

    context.for_user(staff.pk)
    results.publish(session, staff)
    with pytest.raises(ValidationError):
        results.publish(session, staff)

    context.for_user(student.pk)
    assert AssessmentResult.objects.count() == 1
    assert AssessmentResult.objects.update(is_passed=False) == 0

    context.for_user(staff.pk)
    evidence = SimpleUploadedFile("topik.pdf", PDF, content_type="application/pdf")
    external = results.external(
        record,
        world["topik"],
        timezone.localdate() - timedelta(days=30),
        True,
        staff,
        230,
        "TOPIK 5",
        "T-1",
        None,
        evidence,
    )
    assert external.get_media(AssessmentResult.EVIDENCE_COLLECTION).count() == 1
    raises_message(
        "This kind does not take external results.",
        lambda: results.external(record, world["english"], timezone.localdate(), True, staff),
    )
    with pytest.raises(ValidationError):
        results.external(record, world["topik"], timezone.localdate() + timedelta(days=1), True, staff)

    context.for_user(student.pk)
    assert AssessmentResult.objects.count() == 2

    response = signed_in(student).get(f"/assessment-results/{external.pk}/evidence/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert signed_in(stranger).get(f"/assessment-results/{external.pk}/evidence/").status_code == 403
    page = signed_in(student).get("/portal/assessments/").content.decode()
    assert "TOPIK 5" in page
    assert "80.0" in page

    context.for_user(staff.pk)
    results.remove(external, staff, "Wrong student")
    assert AssessmentResult.objects.count() == 1
    context.for_system("test")
    assert ActivityLog.objects.filter(event="assessment.result_removed").exists()


def test_imports_results_from_a_csv_and_reports_problems(world: dict[str, Any], tmp_path: Path) -> None:
    register, session, record, staff = world["register"], world["session"], world["record"], world["staff"]
    other = StudentRecordFactory()
    unregistered = StudentRecordFactory()
    register.register(session, record, staff, by_staff=True)
    register.register(session, other, staff, by_staff=True)
    path = tmp_path / "results.csv"
    path.write_text(
        "\n".join(
            [
                "student_number,listening,reading,writing,grammar,absent,note",
                f"{record.student_number},20,20,20,20,,Good",
                f"{other.student_number},,,,,Y,",
                f"{unregistered.student_number},25,25,25,25,,",
                "00000000,1,1,1,1,,",
            ]
        ),
        encoding="utf-8",
    )
    held = session.held_date.isoformat()

    def run(*args: str, **options: Any) -> tuple[int, str]:
        out, err = StringIO(), StringIO()
        code = call_command("assessment_import_results", *args, stdout=out, stderr=err, **options)
        return int(code), out.getvalue() + err.getvalue()

    assert run("NOPE", "2020-01-01", str(path), actor=staff.email)[0] == 1
    code, output = run("ENG_COMP", held, str(path), actor=staff.email, dry_run=True)
    assert code == 2
    assert "Dry run: 4 row(s): 1 recorded, 1 absent, 2 error(s)." in output
    assert AssessmentResult.objects.count() == 0

    # A student who was not registered is reported and skipped, never registered after the fact.
    code, output = run("ENG_COMP", held, str(path), actor=staff.email)
    assert code == 2
    assert "4 row(s): 1 recorded, 1 absent, 2 error(s)." in output
    assert "is not registered for this session" in output
    imported = AssessmentResult.objects.get()
    assert (str(imported.total_score), imported.is_passed, imported.note) == ("80.0", True, "Good")
    assert AssessmentRegistration.objects.get(student_record=other).status == AssessmentRegistrationStatus.ABSENT
    assert not AssessmentRegistration.objects.filter(student_record=unregistered).exists()
    assert ActivityLog.objects.filter(
        event="command.executed", properties__command="assessment_import_results"
    ).exists()

    out = StringIO()
    assert call_command("assessment_publish_results", "ENG_COMP", held, actor=staff.email, stdout=out) == 0
    assert "Published 1 result(s)" in out.getvalue()
    session.refresh_from_db()
    assert session.results_published_at is not None
    assert call_command("assessment_publish_results", "ENG_COMP", held, actor=staff.email, stdout=out, stderr=out) == 1


def test_counts_a_passed_kind_towards_the_curriculum_requirement(world: dict[str, Any]) -> None:
    record, english, staff = world["record"], world["english"], world["staff"]
    requirement_set = CurriculumRequirementSet.objects.create(
        program=record.program,
        program_role=ProgramRole.PRIMARY,
        catalog_year_from=record.catalog_year - 1,
        name={"en": "Requirements", "ko": "요건", "zh-hans": "要求"},
    )
    CurriculumRequirement.objects.create(
        requirement_set=requirement_set, kind=RequirementKind.ASSESSMENT_PASS, assessment_type=english
    )
    error = database_error(
        lambda: CurriculumRequirement.objects.create(
            requirement_set=requirement_set, kind=RequirementKind.ASSESSMENT_PASS
        )
    )
    assert error is not None and "curriculum_requirements_kind_check" in error

    check = AssessmentPassCheck()
    assert [row.passed for row in check.required(record)] == [False]
    assert check.has_passed(record, english) is False

    registration = world["register"].register(world["session"], record, staff, by_staff=True)
    world["results"].for_registration(registration, scores([20, 20, 20, 20]), None, staff)
    assert [row.passed for row in check.required(record)] == [True]
    assert check.has_passed(record, english) is True

    page = signed_in(world["student"]).get("/portal/assessments/").content.decode()
    assert "Required by your curriculum" in page
    assert str(english.name) in page


def test_registers_enters_and_cancels_from_the_admin_screens_and_registers_from_the_portal(
    world: dict[str, Any],
) -> None:
    staff, session, record, english = world["staff"], world["session"], world["record"], world["english"]
    client = signed_in(staff)
    for url in (
        "/admin/assessment/assessmenttype/",
        f"/admin/assessment/assessmenttype/{english.pk}/change/",
        "/admin/assessment/assessmentsession/",
        "/admin/assessment/assessmentsession/add/",
        f"/admin/assessment/assessmentsession/{session.pk}/change/",
        "/admin/assessment/assessmentresult/",
    ):
        assert client.get(url).status_code == 200, url

    base = f"/admin/assessment/assessmentsession/{session.pk}"
    response = client.post(f"{base}/register-student/", {"student_number": record.student_number})
    assert response.status_code == 302
    registration = AssessmentRegistration.objects.get()
    assert registration.registered_by_id == staff.pk

    url = f"{base}/registrations/{registration.pk}/result/"
    assert client.get(url).status_code == 200
    response = client.post(url, {f"score_{code}": "25" for code in ("LISTENING", "READING", "WRITING", "GRAMMAR")})
    assert response.status_code == 302
    assert AssessmentResult.objects.get(registration=registration).is_passed is True
    # With a result the registration cannot be cancelled (no row link either).
    content = client.get(f"{base}/change/").content.decode()
    assert f"/registrations/{registration.pk}/cancel/" not in content

    response = client.post(
        "/admin/assessment/assessmentresult/record-external/",
        {
            "student_number": record.student_number,
            "assessment_type": world["topik"].pk,
            "taken_date": timezone.localdate().isoformat(),
            "passed": "1",
            "level": "TOPIK 6",
        },
    )
    assert response.status_code == 302
    assert AssessmentResult.objects.filter(level="TOPIK 6").exists()

    other = StudentRecordFactory()
    portal = signed_in(student_of(other))
    page = portal.get("/portal/assessments/").content.decode()
    assert ">Register<" in page
    page = portal.post("/portal/assessments/", {"action": "register", "session_id": session.pk}, follow=True)
    assert "You are registered." in page.content.decode()
    page = portal.post("/portal/assessments/", {"action": "register", "session_id": session.pk}, follow=True)
    assert "Already registered for this session." in page.content.decode()
    assert AssessmentRegistration.objects.filter(student_record=other).exists()


def test_the_schema_restricts_deleting_a_session_with_registrations(world: dict[str, Any]) -> None:
    """Legacy deletions orphaned the rows: the foreign key restricts (``on_delete=PROTECT``)."""
    world["register"].register(world["session"], world["record"], world["staff"], by_staff=True)
    with connection.cursor() as cursor:
        error = database_error(
            lambda: cursor.execute("DELETE FROM assessment_sessions WHERE id = %s", [world["session"].pk])
        )
    assert error is not None and "assessment_registrations_assessment_session_id_foreign" in error
