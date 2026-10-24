"""Original tests/Database/Foundation/TimeZoneTest.php (ADR 0006 offset issue does not occur:
psycopg 3 sends aware datetimes). Uses raw SQL until term models exist (Phase 1 adds the
model based variant)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.db import connection


@pytest.mark.django_db
def test_times_in_other_zones_compare_as_the_same_instant() -> None:
    seoul = datetime(2026, 11, 10, 10, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    with connection.cursor() as cursor:
        cursor.execute("SELECT %s::timestamptz = '2026-11-10 01:00+00'::timestamptz", [seoul])
        assert cursor.fetchone()[0] is True
