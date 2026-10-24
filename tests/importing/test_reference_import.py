"""Original tests/Feature/Reference/ReferenceImportTest.php (``reference_import``)."""

from __future__ import annotations

from collections.abc import Callable
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.utils import translation

from ninefruits.facility.models import Building, Room
from ninefruits.importing.models import Import
from ninefruits.institution.models import LookupValue
from ninefruits.organization.models import OrgUnit
from tests.factories.security import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("reference_data")]

CsvFile = Callable[[str, list[list[str]]], str]


@pytest.fixture(autouse=True)
def operator() -> Any:
    return UserFactory(email="ops@example.com")


def run(type_key: str, path: str, **options: Any) -> tuple[int, str]:
    out, err = StringIO(), StringIO()
    options.setdefault("actor", "ops@example.com")
    with translation.override("en"):
        status = call_command("reference_import", type_key, path, stdout=out, stderr=err, **options)
    return status, out.getvalue() + err.getvalue()


def codes() -> list[str]:
    return sorted(OrgUnit.objects.values_list("code", flat=True))


def test_imports_org_units_with_parents_and_translations_and_updates_on_a_second_import(csv_file: CsvFile) -> None:
    path = csv_file(
        "org.csv",
        [
            ["code", "type", "parent", "name_en", "name_ko", "effective_start_date"],
            ["UNI", "university", "", "Sample University", "샘플대학교", "1990-03-01"],
            ["ENG", "college", "UNI", "College of Engineering", "공과대학", "1990-03-01"],
            ["CSE", "department", "ENG", "Computer Science", "컴퓨터공학과", "1995-03-01"],
        ],
    )
    assert run("org_units", path)[0] == 0

    department = OrgUnit.objects.get(code="CSE")
    assert department.parent.code == "ENG"
    assert department.name_translations == {"en": "Computer Science", "ko": "컴퓨터공학과"}

    update = csv_file(
        "update.csv",
        [
            ["code", "type", "parent", "name_en", "name_zh_CN", "effective_start_date"],
            ["CSE", "department", "ENG", "Computer Science and Engineering", "计算机工程系", "1995-03-01"],
        ],
    )
    assert run("org_units", update)[0] == 0

    department.refresh_from_db()
    assert OrgUnit.objects.filter(code="CSE").count() == 1
    assert department.name_translations == {
        "en": "Computer Science and Engineering",
        "ko": "컴퓨터공학과",
        "zh-hans": "计算机工程系",
    }


def test_reports_failed_rows_and_imports_the_rest(csv_file: CsvFile) -> None:
    path = csv_file(
        "org.csv",
        [
            ["code", "type", "parent", "name_en", "effective_start_date"],
            ["UNI", "university", "", "Sample University", "1990-03-01"],
            ["BAD", "no_such_type", "UNI", "Unknown type", "1990-03-01"],
            ["NONAME", "college", "UNI", "", "1990-03-01"],
            ["LATE", "college", "UNI", "Ends before start", "2020-03-01"],
        ],
    )

    status, output = run("org_units", path)

    assert status == 2
    assert codes() == ["LATE", "UNI"]
    run_record = Import.objects.get()
    assert (run_record.total_rows, run_record.successful_rows, run_record.failed_rows_count()) == (4, 2, 2)
    assert run_record.completed_at is not None
    assert 'Unknown type code "no_such_type".' in output
    assert "The name en field is required." in output


def test_rejects_a_row_the_database_refuses_without_losing_the_other_rows(csv_file: CsvFile) -> None:
    path = csv_file(
        "org.csv",
        [
            ["code", "type", "parent", "name_en", "effective_start_date", "effective_end_date"],
            ["UNI", "university", "", "Sample University", "1990-03-01", ""],
            ["BADRANGE", "college", "UNI", "Bad range", "2020-03-01", "2019-01-01"],
            ["OK", "college", "UNI", "Fine", "2020-03-01", ""],
        ],
    )

    assert run("org_units", path)[0] == 2
    assert codes() == ["OK", "UNI"]


def test_keeps_rows_the_database_rejects_as_failed_rows_with_the_reason(csv_file: CsvFile) -> None:
    """A database error (here the cycle trigger) fails that row only, in its savepoint."""
    path = csv_file(
        "org.csv",
        [
            ["code", "type", "parent", "name_en", "effective_start_date"],
            ["UNI", "university", "", "Sample University", "1990-03-01"],
            ["UNI", "university", "UNI", "Own parent", "1990-03-01"],
            ["ENG", "college", "UNI", "Engineering", "1990-03-01"],
        ],
    )

    assert run("org_units", path)[0] == 2
    assert codes() == ["ENG", "UNI"]
    failed = Import.objects.get().failed_rows.get()
    assert failed.validation_error.startswith("Rejected by the database:")
    assert failed.data["name_en"] == "Own parent"


def test_imports_buildings_rooms_with_room_types_and_code_values(csv_file: CsvFile) -> None:
    buildings = csv_file("b.csv", [["code", "name_en", "name_ko"], ["SCI", "Science Hall", "과학관"]])
    assert run("buildings", buildings)[0] == 0

    rooms = csv_file(
        "r.csv",
        [
            ["building", "code", "room_type", "capacity"],
            ["SCI", "101", "lecture", "60"],
            ["SCI", "102", "unknown", "30"],
        ],
    )
    assert run("rooms", rooms)[0] == 2

    values = csv_file(
        "l.csv",
        [
            ["type", "code", "name_en", "name_ko"],
            ["ethnicity", "han", "Han", "한족"],
            ["ethnicity", "korean", "Korean", "조선족"],
        ],
    )
    assert run("lookup_values", values)[0] == 0

    room = Room.objects.select_related("room_type").get(code="101")
    assert str(Building.objects.get(code="SCI").name) == "Science Hall"
    assert room.capacity == 60
    assert room.room_type is not None and room.room_type.code == "lecture"
    assert not Room.objects.filter(code="102").exists()
    assert LookupValue.objects.of_type("ethnicity").count() == 2


def test_checks_the_header_in_a_dry_run_without_importing(csv_file: CsvFile) -> None:
    missing = csv_file("missing.csv", [["code", "name_en"], ["UNI", "Sample"]])
    valid = csv_file(
        "valid.csv",
        [["code", "type", "name_en", "effective_start_date"], ["UNI", "university", "Sample", "1990-03-01"]],
    )

    status, output = run("org_units", missing, dry_run=True)
    assert status == 1
    assert "Missing required columns" in output

    assert run("org_units", valid, dry_run=True)[0] == 0
    assert OrgUnit.objects.count() == 0


def test_requires_an_actor_account(csv_file: CsvFile) -> None:
    path = csv_file(
        "valid.csv",
        [["code", "type", "name_en", "effective_start_date"], ["UNI", "university", "Sample", "1990-03-01"]],
    )
    out, err = StringIO(), StringIO()

    assert call_command("reference_import", "org_units", path, stdout=out, stderr=err) == 1
    assert OrgUnit.objects.count() == 0


def test_imports_in_chunks_through_the_queue(csv_file: CsvFile) -> None:
    rows = [["code", "type", "name_en", "effective_start_date"]] + [
        [f"U{index:03d}", "university", f"Unit {index}", "1990-03-01"] for index in range(25)
    ]

    assert run("org_units", csv_file("many.csv", rows), chunk=10)[0] == 0

    run_record = Import.objects.get()
    assert (run_record.processed_rows, run_record.successful_rows) == (25, 25)
    assert OrgUnit.objects.count() == 25
