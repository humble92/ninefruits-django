"""Original tests/Feature/Curriculum/CourseTest.php.

Phase 4 completion criterion: versions of one course never overlap (exclusion constraint), and
revising a course keeps earlier sections on their version."""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction

from ninefruits.curriculum.actions import ReviseCourse
from ninefruits.curriculum.enums import ProgramRole, RequisiteKind
from ninefruits.curriculum.models import Course, CourseRequisite, CurriculumRequirementSet
from tests.factories.curriculum import CourseFactory, CourseVersionFactory, CurriculumRequirementSetFactory
from tests.factories.organization import OrgUnitFactory, ProgramFactory
from tests.factories.security import UserFactory

pytestmark = pytest.mark.django_db


def test_refuses_overlapping_versions_of_a_course_in_the_database() -> None:
    course = CourseFactory(version={"effective_start_date": date(2020, 3, 1), "effective_end_date": date(2024, 2, 29)})

    with pytest.raises(IntegrityError, match="course_versions_no_overlap_excl"), transaction.atomic():
        CourseVersionFactory(course=course, effective_start_date=date(2023, 3, 1))

    CourseVersionFactory(course=course, effective_start_date=date(2024, 3, 1))
    assert course.version_on("2025-05-01").effective_start_date == date(2024, 3, 1)
    assert course.version_on("2021-05-01").effective_start_date == date(2020, 3, 1)


def test_revises_a_course_from_a_date_copying_requisites_and_keeping_the_old_version() -> None:
    prerequisite = CourseFactory()
    course = CourseFactory(version={"credits": 3, "title": {"en": "Data Structures", "ko": "자료구조"}})
    old = course.versions.get()
    CourseRequisite.objects.create(course_version=old, kind=RequisiteKind.PREREQUISITE, required_course=prerequisite)

    new = ReviseCourse()(course, date(2027, 3, 1), {"credits": 4}, UserFactory(), "Lab added")

    old.refresh_from_db()
    new.refresh_from_db()
    assert old.effective_end_date == date(2027, 2, 28)
    assert new.credits == Decimal("4.0")
    assert new.title_translations == {"en": "Data Structures", "ko": "자료구조"}
    assert list(new.requisites.values_list("required_course_id", flat=True)) == [prerequisite.pk]
    with pytest.raises(ValidationError):
        ReviseCourse()(course, date(2027, 3, 1), {}, UserFactory())


def test_keeps_requirement_sets_of_a_program_and_role_from_overlapping_in_catalog_years() -> None:
    program = ProgramFactory()
    CurriculumRequirementSetFactory(program=program, catalog_year_from=2015, catalog_year_to=2022)
    CurriculumRequirementSetFactory(program=program, catalog_year_from=2023)
    CurriculumRequirementSetFactory(program=program, program_role=ProgramRole.MINOR, catalog_year_from=2015)

    with pytest.raises(IntegrityError, match="curriculum_requirement_sets_no_overlap_excl"), transaction.atomic():
        CurriculumRequirementSetFactory(program=program, catalog_year_from=2022)
    assert CurriculumRequirementSet.applicable(program.pk, ProgramRole.PRIMARY, 2024).catalog_year_from == 2023
    assert CurriculumRequirementSet.applicable(program.pk, ProgramRole.PRIMARY, 2018).catalog_year_to == 2022


def test_imports_courses_and_revisions_from_csv_failing_only_bad_rows(essential_data: None, tmp_path: Path) -> None:
    unit = OrgUnitFactory(code="CSE")
    UserFactory(email="ops@example.com")
    path = tmp_path / "courses.csv"
    path.write_text(
        "\n".join(
            [
                "code,org_unit,effective_start_date,effective_end_date,title_en,title_ko,credits",
                "CSE2010,CSE,2015-03-01,2026-02-28,Data Structures,자료구조,3",
                "CSE2010,,2026-03-01,,Data Structures,자료구조,4",
                "CSE9999,NOPE,2015-03-01,,Ghost,,3",
                "CSE2010,,2020-03-01,,Overlapping,,3",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    status = call_command(
        "reference_import", "courses", str(path), actor="ops@example.com", stdout=io.StringIO(), stderr=io.StringIO()
    )

    assert status == 2
    course = Course.objects.get(code="CSE2010")
    assert course.org_unit_id == unit.pk
    assert course.versions.count() == 2
    assert course.version_on("2026-05-01").credits == Decimal("4.0")
    assert not Course.objects.filter(code="CSE9999").exists()
