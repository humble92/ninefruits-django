"""Beyond the original ``GraduationTest``: degree numbers from the pattern (sequence per prefix,
tokens, a pattern without ``{SEQ:n}``), audits of second majors and minors, the examination
requirement through ``AssessmentPassCheck``, the GPA from the latest term record and the snapshot
stored with an audit."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from django.utils import timezone

from ninefruits.assessment.models import AssessmentResult, AssessmentType
from ninefruits.curriculum.enums import ProgramRole, RequirementKind
from ninefruits.curriculum.models import CurriculumRequirement, CurriculumRequirementSet
from ninefruits.grading.models import TermRecord
from ninefruits.graduation.actions import RunDegreeAudits
from ninefruits.graduation.services import DegreeAudit, DegreeNumberGenerator
from ninefruits.graduation.settings import DEGREE_NUMBER_PATTERN, GraduationSettings
from ninefruits.person.enums import AdditionalProgramRole
from ninefruits.person.models import StudentRecordProgram
from tests.factories.organization import ProgramFactory

from .conftest import set_minimum_gpa

pytestmark = pytest.mark.django_db


def settings_with(pattern: str) -> GraduationSettings:
    settings = GraduationSettings.load()
    settings.degree_number_pattern = pattern
    return settings


def test_issues_degree_numbers_per_prefix(world: dict[str, Any]) -> None:
    cs, ee = ProgramFactory(code="CS"), ProgramFactory(code="EE")
    numbers = DegreeNumberGenerator(settings_with("{PROGRAM}-{YYYY}-{SEQ:5}"))
    assert numbers.next(cs, date(2026, 2, 20)) == "CS-2026-00001"
    assert numbers.next(cs, date(2026, 8, 20)) == "CS-2026-00002"
    assert numbers.next(ee, date(2026, 2, 20)) == "EE-2026-00001"
    assert numbers.next(cs, date(2027, 2, 20)) == "CS-2027-00001"
    assert DegreeNumberGenerator(settings_with("D{YY}-{SEQ:3}/{PROGRAM}")).next(cs, date(2026, 2, 20)) == "D26-001/CS"
    with pytest.raises(ValueError, match="SEQ"):
        DegreeNumberGenerator(settings_with("{PROGRAM}-{YYYY}")).next(cs, date(2026, 2, 20))


def test_the_settings_form_accepts_only_known_tokens_and_one_sequence() -> None:
    assert DEGREE_NUMBER_PATTERN.match("{PROGRAM}-{YYYY}-{SEQ:5}")
    assert DEGREE_NUMBER_PATTERN.match("B{YY}{SEQ:4}")
    assert not DEGREE_NUMBER_PATTERN.match("{PROGRAM}-{YYYY}")
    assert not DEGREE_NUMBER_PATTERN.match("{TYPE}-{SEQ:5}")
    assert not DEGREE_NUMBER_PATTERN.match("{SEQ:5}-{SEQ:2}")


def test_audits_second_majors_and_minors_without_the_gpa_minimum(world: dict[str, Any]) -> None:
    record = world["record"]
    second, minor = ProgramFactory(code="MATH"), ProgramFactory(code="ART")
    for program, role in ((second, AdditionalProgramRole.SECOND_MAJOR), (minor, AdditionalProgramRole.MINOR)):
        StudentRecordProgram.objects.create(
            student_record=record, program=program, role=role, start_date=date(2024, 3, 1)
        )
    CurriculumRequirementSet.objects.create(
        program=minor,
        program_role=ProgramRole.MINOR,
        catalog_year_from=2020,
        total_credits=Decimal("0"),
        name={"en": "Minor"},
    )
    set_minimum_gpa(2.0)
    results = DegreeAudit().evaluate_all(record)
    assert [(result.role, result.program.code) for result in results] == [
        (ProgramRole.PRIMARY, record.program.code),
        (ProgramRole.SECOND_MAJOR, "MATH"),
        (ProgramRole.MINOR, "ART"),
    ]
    assert results[1].issues == ["No graduation requirements are defined for catalog year 2024."]
    assert results[2].is_satisfied() is True
    assert results[2].minimum_gpa is None
    assert "Cumulative GPA - below the minimum 2." in results[0].issues

    stored = RunDegreeAudits().for_record(record, None)
    assert [audit.program_role for audit in stored] == ["primary", "second_major", "minor"]
    assert stored[2].is_satisfied is True


def test_judges_the_examination_requirement_and_the_latest_gpa(world: dict[str, Any], profile: None) -> None:
    record, requirement_set = world["record"], world["set"]
    english = AssessmentType.objects.get(code="ENG_COMP")
    line = CurriculumRequirement.objects.create(
        requirement_set=requirement_set, kind=RequirementKind.ASSESSMENT_PASS, assessment_type=english, sort_order=4
    )
    result = DegreeAudit().evaluate(record, record.program, ProgramRole.PRIMARY)
    exam = result.requirements[-1]
    assert exam.requirement_id == line.pk
    assert exam.name == str(english.name)
    assert exam.is_satisfied is False
    AssessmentResult.objects.create(
        student_record=record,
        assessment_type=english,
        taken_date=timezone.localdate() - timedelta(days=30),
        is_passed=True,
        source="external",
        entered_at=timezone.now(),
    )
    assert DegreeAudit().evaluate(record, record.program, ProgramRole.PRIMARY).requirements[-1].is_satisfied is True

    from tests.factories.term import TermFactory

    older, newer = world["term"], TermFactory(start_date=date(2025, 9, 1), end_date=date(2025, 12, 20))
    now = timezone.now()
    TermRecord.objects.create(student_record=record, term=older, cumulative_gpa=Decimal("1.9"), calculated_at=now)
    TermRecord.objects.create(student_record=record, term=newer, cumulative_gpa=Decimal("3.25"), calculated_at=now)
    set_minimum_gpa(3.0)
    result = DegreeAudit().evaluate(record, record.program, ProgramRole.PRIMARY)
    assert result.cumulative_gpa == Decimal("3.25")
    assert not any("GPA" in issue for issue in result.issues)
    snapshot = result.to_dict()
    assert snapshot["cumulative_gpa"] == 3.25
    assert snapshot["minimum_gpa"] == 3.0
    assert snapshot["requirements"][-1]["kind"] == "assessment_pass"
    assert set(snapshot) == {
        "program_id",
        "program_code",
        "role",
        "set_id",
        "earned_credits",
        "required_credits",
        "cumulative_gpa",
        "minimum_gpa",
        "satisfied",
        "issues",
        "requirements",
    }
