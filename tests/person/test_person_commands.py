"""``people_find_duplicates`` (original tests/Feature/Security/SecurityCommandsTest.php, "lists
likely duplicate people")."""

from __future__ import annotations

from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from tests.factories.person import PersonFactory

pytestmark = pytest.mark.django_db


def run() -> tuple[int, str]:
    out, err = StringIO(), StringIO()
    status = call_command("people_find_duplicates", stdout=out, stderr=err)
    return int(status or 0), out.getvalue() + err.getvalue()


def test_lists_likely_duplicate_people() -> None:
    assert run() == (0, "No likely duplicates.\n")

    PersonFactory(national_id="TEST-1")
    PersonFactory(national_id="TEST-1")
    PersonFactory(family_name="Kim", given_name="Minsu", birth_date=date(2001, 2, 3))
    PersonFactory(family_name="kim", given_name="MINSU", birth_date=date(2001, 2, 3))

    status, output = run()
    assert status == 2
    assert "national_id" in output
    assert "name_birth_date" in output


def test_leaves_merged_people_out() -> None:
    keep = PersonFactory(national_id="TEST-2")
    PersonFactory(national_id="TEST-2", merged_into=keep)

    assert run()[0] == 0
