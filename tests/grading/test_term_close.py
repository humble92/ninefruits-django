"""Term close (original ``tests/Feature/Grading/TermCloseTest.php``): academic standing (warnings,
dismissal review, consecutive warnings, regular terms only), honors ranks per program, the
preflight, later cumulative GPAs after a grade change. The close runs as a Celery chord
(eager in tests) with its progress in ``job_batches``."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from django.core.exceptions import ValidationError

from ninefruits.core.batches import JobBatch
from ninefruits.grading.actions import CloseTerm, ManageGradeChanges
from ninefruits.grading.enums import AcademicStanding, EvaluationMethod
from ninefruits.grading.models import TermRecord
from ninefruits.registration.models import Enrollment
from ninefruits.security.enums import Permission
from ninefruits.term.enums import TermStatus
from tests.factories.offering import SectionFactory
from tests.factories.organization import ProgramFactory
from tests.factories.person import StudentRecordFactory
from tests.factories.registration import EnrollmentFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory, TermTypeFactory

from .conftest import set_grading

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(korean_scale: Any, django_capture_on_commit_callbacks: Any) -> dict[str, Any]:
    set_grading(warning_gpa_below=1.75, dismissal_warning_count=3, honors_min_gpa=4.0, honors_min_credits=6)
    return {
        "staff": UserFactory(permissions=[Permission.GRADES_MANAGE, Permission.GRADE_CHANGES_APPROVE]),
        "regular": TermTypeFactory(is_regular=True),
        "summer": TermTypeFactory(is_regular=False),
        "program": ProgramFactory(),
        "capture": django_capture_on_commit_callbacks,
    }


def closing_term(term_type: Any, start: str) -> Any:
    first = date.fromisoformat(start)
    return TermFactory(published=True, start_date=first, end_date=first + timedelta(days=100), term_type=term_type)


def final_grades(record: Any, term: Any, grades: list[str]) -> None:
    """Finalized grades of the student in the term, 3 credits each."""
    for grade in grades:
        EnrollmentFactory(
            section=SectionFactory(term=term, published=True), grade=grade, student_record=record, credits=3
        )


def close_now(world: dict[str, Any], term: Any) -> TermRecord:
    term.refresh_from_db()
    with world["capture"](execute=True):
        CloseTerm().close(term, world["staff"], "End of term")
    return TermRecord.objects.filter(term=term).first()


def test_warns_below_the_threshold_and_flags_dismissal_review_after_the_third_warning(world: dict[str, Any]) -> None:
    student = StudentRecordFactory(program=world["program"])
    standings = []
    for index, term_grades in enumerate([["D0", "F"], ["B0", "B0"], ["D0", "D0"], ["F", "D+"]]):
        term = closing_term(world["regular"], f"{2023 + index}-03-01")
        final_grades(student, term, term_grades)
        record = close_now(world, term)
        standings.append((record.academic_standing, record.warning_count))
        term.refresh_from_db()
        assert term.status == TermStatus.GRADES_CLOSED
        assert record.closed_at is not None

    assert standings == [
        (AcademicStanding.WARNING, 1),
        (AcademicStanding.GOOD, 1),
        (AcademicStanding.WARNING, 2),
        (AcademicStanding.DISMISSAL_REVIEW, 3),
    ]
    student.refresh_from_db()
    assert student.academic_standing == "dismissal_review"


def test_counts_only_consecutive_warnings_when_set_and_leaves_summer_terms_out(world: dict[str, Any]) -> None:
    set_grading(dismissal_consecutive_only=True, dismissal_warning_count=2)
    student = StudentRecordFactory(program=world["program"])
    spring = closing_term(world["regular"], "2025-03-01")
    final_grades(student, spring, ["F", "D0"])
    summer = closing_term(world["summer"], "2025-06-25")
    final_grades(student, summer, ["F"])
    fall = closing_term(world["regular"], "2025-09-01")
    final_grades(student, fall, ["D0", "D0"])

    assert close_now(world, spring).academic_standing == AcademicStanding.WARNING
    summer_record = close_now(world, summer)
    assert (summer_record.academic_standing, summer_record.warning_count) == (None, 1)
    fall_record = close_now(world, fall)
    assert (fall_record.academic_standing, fall_record.warning_count) == (AcademicStanding.DISMISSAL_REVIEW, 2)


def test_gives_no_warning_for_a_term_of_pass_fail_courses_only(world: dict[str, Any]) -> None:
    student = StudentRecordFactory(program=world["program"])
    term = closing_term(world["regular"], "2025-03-01")
    final_grades(student, term, ["P", "NP"])

    record = close_now(world, term)
    assert record.term_gpa is None
    assert record.academic_standing == AcademicStanding.GOOD


def test_ranks_honors_per_program_with_ties_and_without_failing_students(world: dict[str, Any]) -> None:
    term = closing_term(world["regular"], "2025-03-01")
    students = {
        "first": ["A+", "A+"],  # 4.50
        "tied": ["A+", "A+"],  # 4.50
        "third": ["A+", "A0"],  # 4.25
        "failed one": ["A+", "A+", "NP"],  # 4.50, but a failed course
        "few credits": ["A+"],  # 3 credits < 6
    }
    records = {}
    for name, grades in students.items():
        records[name] = StudentRecordFactory(program=world["program"])
        final_grades(records[name], term, grades)
    other = StudentRecordFactory(program=ProgramFactory())
    final_grades(other, term, ["A0", "A0"])

    close_now(world, term)

    def rank(record: Any) -> int | None:
        return TermRecord.objects.get(student_record=record).honors_rank

    assert rank(records["first"]) == 1
    assert rank(records["tied"]) == 1
    assert rank(records["third"]) == 3
    assert rank(records["failed one"]) is None
    assert rank(records["few credits"]) is None
    assert rank(other) == 1


def test_does_not_close_a_term_with_grades_that_are_not_final(world: dict[str, Any]) -> None:
    term = closing_term(world["regular"], "2025-03-01")
    EnrollmentFactory(section=SectionFactory(term=term, published=True))

    assert len(CloseTerm().preflight(term).open_sections) == 1
    with pytest.raises(ValidationError):
        CloseTerm().close(term, world["staff"])
    term.refresh_from_db()
    assert term.status == TermStatus.PUBLISHED


def test_recalculates_later_cumulative_gpas_when_an_earlier_grade_changes(world: dict[str, Any]) -> None:
    student = StudentRecordFactory(program=world["program"])
    first = closing_term(world["regular"], "2025-03-01")
    final_grades(student, first, ["C0"])
    second = closing_term(world["regular"], "2025-09-01")
    final_grades(student, second, ["A0"])
    close_now(world, first)
    assert str(close_now(world, second).cumulative_gpa) == "3.00"

    enrollment = Enrollment.objects.select_related("section", "version").get(term=first)
    enrollment.section.evaluation_method = EvaluationMethod.RELATIVE
    enrollment.section.save(update_fields=["evaluation_method"])
    changes = ManageGradeChanges()
    requester = UserFactory(permissions=[Permission.GRADE_CHANGES_REQUEST])
    changes.approve(changes.request(enrollment, "B0", "Exam re-marked", requester), world["staff"])

    record = TermRecord.objects.get(term=second)
    assert str(record.cumulative_gpa) == "3.50"
    assert record.closed_at is not None


def test_runs_as_a_batch_of_student_chunks_with_progress_and_tells_the_staff(
    world: dict[str, Any], mailoutbox: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from ninefruits.grading.actions import close_term

    monkeypatch.setattr(close_term, "CHUNK", 2)
    term = closing_term(world["regular"], "2025-03-01")
    for _index in range(5):
        final_grades(StudentRecordFactory(program=world["program"]), term, ["B0"])

    close_now(world, term)

    batch = JobBatch.objects.get(name=f"term-close:{term.code}")
    assert (batch.total_jobs, batch.pending_jobs, batch.failed_jobs) == (3, 0, 0)
    assert batch.finished_at is not None
    assert batch.progress() == 100
    assert TermRecord.objects.filter(term=term, closed_at__isnull=False).count() == 5
    assert [message.to for message in mailoutbox] == [[world["staff"].email]]
    assert "5 term record(s)" in mailoutbox[0].body


def test_a_failed_chunk_marks_the_batch_and_the_term_stays_open(
    world: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    term = closing_term(world["regular"], "2025-03-01")
    final_grades(StudentRecordFactory(program=world["program"]), term, ["B0"])

    def broken(self: Any, term: Any, record_ids: list[int]) -> int:
        raise RuntimeError("worker lost")

    monkeypatch.setattr(CloseTerm, "close_records", broken)
    with pytest.raises(RuntimeError):
        close_now(world, term)

    batch = JobBatch.objects.get(name=f"term-close:{term.code}")
    assert batch.failed_jobs == 1
    assert batch.finished_at is None
    term.refresh_from_db()
    assert term.status == TermStatus.PUBLISHED
