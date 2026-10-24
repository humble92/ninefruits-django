"""Original tests/Feature/Organization/ReorganizeOrgUnitTest.php."""

from __future__ import annotations

from datetime import date

import pytest
from django.core.exceptions import ValidationError

from ninefruits.audit.models import ActivityLog
from ninefruits.organization.actions import ReorganizeOrgUnit
from ninefruits.organization.enums import OrgUnitChangeType
from ninefruits.organization.models import OrgUnit
from tests.factories.organization import OrgUnitFactory

pytestmark = pytest.mark.django_db


def test_ends_the_unit_the_day_before_and_links_the_successor() -> None:
    old = OrgUnitFactory(effective_start_date=date(2000, 3, 1))
    new = OrgUnitFactory(effective_start_date=date(2025, 3, 1))

    ReorganizeOrgUnit()(old, OrgUnitChangeType.MERGED, [new], date(2025, 3, 1), "Merger")

    succession = old.successions.get()
    old.refresh_from_db()
    assert old.effective_end_date == date(2025, 2, 28)
    assert succession.successor_id == new.pk
    assert succession.change_type == OrgUnitChangeType.MERGED
    assert not OrgUnit.objects.effective_on(date(2025, 3, 1)).filter(pk=old.pk).exists()
    assert ActivityLog.objects.get(event="org_unit.reorganized").reason == "Merger"


def test_allows_several_successors_only_for_a_split() -> None:
    with pytest.raises(ValidationError):
        ReorganizeOrgUnit()(
            OrgUnitFactory(), OrgUnitChangeType.MERGED, [OrgUnitFactory(), OrgUnitFactory()], date(2025, 3, 1), "x"
        )


def test_records_a_split_into_several_units() -> None:
    old = OrgUnitFactory()
    first, second = OrgUnitFactory(), OrgUnitFactory()

    ReorganizeOrgUnit()(old, OrgUnitChangeType.SPLIT, [first, second], date(2025, 3, 1), "Split")

    assert sorted(old.successions.values_list("successor_id", flat=True)) == sorted([first.pk, second.pk])


def test_rejects_an_effective_date_before_the_unit_started() -> None:
    old = OrgUnitFactory(effective_start_date=date(2020, 3, 1))
    with pytest.raises(ValidationError):
        ReorganizeOrgUnit()(old, OrgUnitChangeType.RENAMED, [OrgUnitFactory()], date(2019, 1, 1), "x")
