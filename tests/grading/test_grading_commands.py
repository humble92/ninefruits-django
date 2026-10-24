"""Grading commands (original ``tests/Feature/Grading/GradingCommandsTest.php``): ``term_close``,
``grades_recalculate``, ``grades_remind_missing``."""

from __future__ import annotations

import io
from typing import Any

import pytest
from django.core.management import call_command

from ninefruits.grading.models import TermRecord
from ninefruits.term.enums import TermStatus
from tests.factories.offering import SectionFactory
from tests.factories.person import InstructorFactory
from tests.factories.registration import EnrollmentFactory

from .conftest import teacher_of, term_between

pytestmark = pytest.mark.django_db


@pytest.fixture
def world(korean_scale: Any) -> dict[str, Any]:
    term = term_between("2025-03-01", "2025-06-20")
    section = SectionFactory(term=term, published=True)
    finished = EnrollmentFactory(section=SectionFactory(term=term, published=True), grade="A0")
    return {"term": term, "section": section, "finished": finished}


def run(*args: Any, **options: Any) -> tuple[int, str]:
    out, err = io.StringIO(), io.StringIO()
    code = call_command(*args, stdout=out, stderr=err, **options)
    return int(code or 0), out.getvalue() + err.getvalue()


def test_closes_a_term_only_when_every_grade_is_final(
    world: dict[str, Any], django_capture_on_commit_callbacks: Any
) -> None:
    term, section = world["term"], world["section"]
    open_enrollment = EnrollmentFactory(section=section)

    assert run("term_close", "NOPE")[0] == 1
    code, output = run("term_close", term.code)
    assert code == 2
    assert f"{section.label()}: 1 grade(s) not finalized." in output

    open_enrollment.__class__.objects.filter(pk=open_enrollment.pk).update(status="withdrawn")

    code, output = run("term_close", term.code, "--dry-run")
    assert code == 0
    assert "Ready to close." in output
    term.refresh_from_db()
    assert term.status == TermStatus.PUBLISHED

    with django_capture_on_commit_callbacks(execute=True):
        code, _output = run("term_close", term.code, "--reason", "End of spring")
    assert code == 0
    term.refresh_from_db()
    assert term.status == TermStatus.GRADES_CLOSED
    record = TermRecord.objects.get(term=term)
    assert str(record.term_gpa) == "4.00"
    assert record.closed_at is not None


def test_recalculates_term_records_with_a_reason(world: dict[str, Any]) -> None:
    term = world["term"]
    assert run("grades_recalculate", "--term", term.code)[0] == 1
    code, output = run("grades_recalculate", "--term", term.code, "--reason", "Policy change")
    assert code == 0
    assert "1 student(s) recalculated." in output
    record = TermRecord.objects.get(student_record_id=world["finished"].student_record_id)
    assert str(record.cumulative_gpa) == "4.00"
    assert run("grades_recalculate", "--student-number", "NOPE", "--reason", "x")[0] == 1


def test_reminds_instructors_of_grades_not_submitted(world: dict[str, Any], mailoutbox: list[Any]) -> None:
    section = world["section"]
    EnrollmentFactory(section=section)
    user = teacher_of(section, InstructorFactory())

    code, output = run("grades_remind_missing", world["term"].code, "--dry-run")
    assert code == 0
    assert "0 reminder(s) sent." in output
    assert mailoutbox == []

    code, output = run("grades_remind_missing", world["term"].code)
    assert code == 0
    assert "1 reminder(s) sent." in output
    assert [message.to for message in mailoutbox] == [[user.email]]
    assert section.label() in mailoutbox[0].body
