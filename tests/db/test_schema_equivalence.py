"""The schema equals the original Laravel schema (porting-plan 2.3, 13.5 item 6). The reference
fingerprint was taken from the original v1.0.0 migrated on PostgreSQL 18.6; see
porting/reference/README.md for how to regenerate it."""

from pathlib import Path

import pytest
from django.db import connections

from ninefruits.core import schema

REFERENCE = Path(__file__).resolve().parents[2] / "porting" / "reference" / "schema-fingerprint.txt"


@pytest.mark.django_db(databases=["default", "migrator"])
def test_schema_matches_the_original() -> None:
    expected = REFERENCE.read_text(encoding="utf-8").splitlines()
    with connections["migrator"].cursor() as cursor:
        actual = schema.fingerprint(cursor)
    difference = schema.diff(expected, actual)
    assert difference == [], "\n".join(difference[:50])
