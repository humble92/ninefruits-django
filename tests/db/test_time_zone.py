"""Original tests/Database/Foundation/TimeZoneTest.php (ADR 0006 offset issue does not occur:
psycopg 3 sends aware datetimes): a raw SQL check and the model based cases of the original
(term windows and org unit dates)."""

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


@pytest.mark.django_db
def test_stores_and_compares_times_in_other_time_zones_as_the_same_instant() -> None:
    from datetime import timedelta

    from ninefruits.term.models import TermWindow
    from tests.factories.term import TermWindowFactory

    seoul = datetime(2026, 11, 10, 10, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    window = TermWindowFactory(opens_at=seoul, closes_at=seoul + timedelta(hours=1))
    window.refresh_from_db()

    assert window.opens_at == datetime(2026, 11, 10, 1, 0, tzinfo=ZoneInfo("UTC"))
    assert TermWindow.objects.filter(opens_at__lte=seoul, pk=window.pk).exists()
    assert not TermWindow.objects.filter(opens_at__lt=seoul, pk=window.pk).exists()


@pytest.mark.django_db
def test_keeps_the_local_date_for_date_columns() -> None:
    from ninefruits.organization.models import OrgUnit
    from tests.factories.organization import OrgUnitFactory

    local_midnight = datetime(2026, 3, 2, 0, 0, tzinfo=ZoneInfo("Asia/Seoul"))
    unit = OrgUnitFactory(effective_start_date=local_midnight.date())

    assert OrgUnit.objects.get(pk=unit.pk).effective_start_date.isoformat() == "2026-03-02"
