"""Original tests/Feature/Person/PersonImportTest.php (``reference_import students|instructors``)."""

from __future__ import annotations

import csv
from datetime import date
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from django.core.management import call_command
from django.utils import translation

from ninefruits.person.enums import EmploymentType, StudentStatus
from ninefruits.person.models import Instructor, Person, StudentRecord
from tests.factories.organization import ProgramFactory
from tests.factories.person import PersonFactory, StudentRecordFactory
from tests.factories.security import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("essential_data")]


@pytest.fixture(autouse=True)
def setup() -> Any:
    UserFactory(email="ops@example.com")
    return ProgramFactory(code="B-CSE", effective_start_date=date(2000, 1, 1))


def people_csv(tmp_path: Path, rows: list[list[str]]) -> str:
    path = tmp_path / f"{len(list(tmp_path.iterdir()))}.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)
    return str(path)


def import_people(type_key: str, path: str) -> int:
    with translation.override("en"):
        return int(
            call_command(
                "reference_import", type_key, path, actor="ops@example.com", stdout=StringIO(), stderr=StringIO()
            )
            or 0
        )


def test_imports_students_with_people_and_updates_them_by_student_number(tmp_path: Path, setup: Any) -> None:
    program = setup
    header = ["student_number", "program", "admission_date", "year_level", "status", "family_name", "given_name"]
    path = people_csv(
        tmp_path,
        [
            [*header, "name_ko", "birth_date", "national_id"],
            ["201900001", "B-CSE", "2019-03-01", "4", "enrolled", "Kim", "Minsu", "김민수", "2000-05-01", "TEST-1"],
            ["201900002", "B-CSE", "2019-03-01", "3", "on_leave", "Lee", "Jiwoo", "이지우", "2000-07-01", ""],
            ["201900003", "NOPE", "2019-03-01", "1", "enrolled", "Park", "Bad", "", "", ""],
        ],
    )  # fmt: skip

    assert import_people("students", path) == 2

    record = StudentRecord.objects.get(student_number="201900001")
    assert record.program_id == program.pk
    assert record.org_unit_id == program.org_unit_id
    assert record.catalog_year == 2019
    assert record.person.name_variants == {"ko": "김민수"}
    assert record.person.national_id_encrypted == "TEST-1"
    assert StudentRecord.objects.get(student_number="201900002").status == StudentStatus.ON_LEAVE
    assert not StudentRecord.objects.filter(student_number="201900003").exists()

    update = people_csv(tmp_path, [["student_number", "year_level", "phone"], ["201900001", "4", "010-0000-1111"]])
    assert import_people("students", update) == 0

    person = Person.objects.get(pk=record.person_id)
    assert StudentRecord.objects.count() == 2
    assert person.phone == "010-0000-1111"
    assert person.family_name == "Kim"


def test_attaches_a_readmission_to_the_existing_person_by_national_id(tmp_path: Path, setup: Any) -> None:
    person = PersonFactory(national_id="TEST-0000000009")
    StudentRecordFactory(program=setup, graduated=True, person=person, student_number="201500009")

    path = people_csv(
        tmp_path,
        [
            ["student_number", "program", "admission_date", "family_name", "national_id"],
            ["202600009", "B-CSE", "2026-03-01", "Ignored", "TEST-0000000009"],
        ],
    )
    assert import_people("students", path) == 0

    assert StudentRecord.objects.get(student_number="202600009").person_id == person.pk
    assert Person.objects.count() == 1


def test_imports_instructors_with_translated_titles(tmp_path: Path, setup: Any) -> None:
    path = people_csv(
        tmp_path,
        [
            ["employee_number", "org_unit", "employment_type", "academic_title_en", "academic_title_ko", "family_name"],
            ["F00001", setup.org_unit.code, "full_time", "Professor", "교수", "Choi"],
        ],
    )  # fmt: skip
    assert import_people("instructors", path) == 0

    instructor = Instructor.objects.get(employee_number="F00001")
    assert instructor.employment_type == EmploymentType.FULL_TIME
    assert instructor.academic_title_translations == {"en": "Professor", "ko": "교수"}
    assert instructor.person.family_name == "Choi"


def test_leaves_no_person_behind_when_the_database_rejects_a_row(tmp_path: Path) -> None:
    path = people_csv(
        tmp_path,
        [
            ["student_number", "program", "admission_date", "status", "family_name"],
            # graduated needs a graduation_date (CHECK)
            ["201800077", "B-CSE", "2018-03-01", "graduated", "Orphan"],
        ],
    )
    assert import_people("students", path) == 2

    assert not StudentRecord.objects.filter(student_number="201800077").exists()
    assert not Person.objects.filter(family_name="Orphan").exists()
