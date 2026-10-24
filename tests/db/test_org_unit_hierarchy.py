"""Original tests/Database/Organization/OrgUnitHierarchyTest.php."""

from __future__ import annotations

from datetime import date

import pytest
from django.db import connection

from ninefruits.core.db import session_context
from ninefruits.organization.models import OrgUnit, Program
from ninefruits.security.actions import AssignRole
from ninefruits.security.enums import Permission, ScopeType
from tests.db.support import database_error
from tests.factories.organization import OrgUnitFactory
from tests.factories.security import RoleFactory, UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def units() -> dict[str, OrgUnit]:
    university = OrgUnitFactory()
    college = OrgUnitFactory(parent=university)
    return {
        "university": university,
        "college": college,
        "department": OrgUnitFactory(parent=college),
        "other_college": OrgUnitFactory(parent=university),
    }


def _move(unit: OrgUnit, parent: OrgUnit) -> None:
    unit.parent = parent
    unit.save()


def test_returns_descendants_and_ancestors(units: dict[str, OrgUnit]) -> None:
    assert sorted(OrgUnit.descendant_ids_of([units["college"].pk])) == sorted(
        [units["college"].pk, units["department"].pk]
    )
    assert units["department"].ancestor_ids() == [
        units["department"].pk,
        units["college"].pk,
        units["university"].pk,
    ]


def test_prevents_placing_a_unit_under_itself_or_a_descendant(units: dict[str, OrgUnit]) -> None:
    college = units["college"]
    assert "cannot be placed under itself" in (database_error(lambda: _move(college, units["department"])) or "")
    college.refresh_from_db()
    assert "cannot be placed under itself" in (database_error(lambda: _move(college, college)) or "")
    college.refresh_from_db()
    assert database_error(lambda: _move(college, units["other_college"])) is None


def test_keeps_a_generated_validity_period_for_date_queries() -> None:
    ended = OrgUnitFactory(effective_start_date=date(2000, 3, 1), ended=date(2015, 2, 28))

    assert OrgUnit.objects.effective_on(date(2014, 6, 1)).filter(pk=ended.pk).exists()
    assert not OrgUnit.objects.effective_on(date(2015, 3, 1)).filter(pk=ended.pk).exists()
    assert ended.is_effective_on(date(2015, 2, 28))
    with connection.cursor() as cursor:
        cursor.execute("SELECT effective_period @> %s::date FROM org_units WHERE id = %s", ["2015-02-28", ended.pk])
        assert cursor.fetchone()[0] is True

    def end_before_start() -> None:
        ended.effective_end_date = date(1999, 1, 1)
        ended.save()

    assert "range lower bound must be less than or equal to range upper bound" in (
        database_error(end_before_start) or ""
    )


def test_gives_row_level_security_the_org_units_of_a_scoped_permission_including_descendants(
    units: dict[str, OrgUnit],
) -> None:
    user = UserFactory()
    role = RoleFactory(permissions=[Permission.USERS_VIEW])
    AssignRole()(user, role, "test", ScopeType.ORG_UNIT, units["college"].pk)

    session_context().for_user(user.pk)
    with connection.cursor() as cursor:
        cursor.execute("SELECT util.permission_org_unit_ids('users.view')")
        ids = cursor.fetchone()[0]
    session_context().reset()

    assert sorted(ids) == sorted([units["college"].pk, units["department"].pk])


def test_requires_translatable_names_to_be_json_objects(units: dict[str, OrgUnit]) -> None:
    def insert() -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO programs (code, name, degree_level, org_unit_id, effective_start_date) "
                "VALUES (%s, %s::jsonb, %s, %s, %s)",
                ["X1", '"plain"', "bachelor", units["department"].pk, "2020-01-01"],
            )

    assert "programs_name_object_check" in (database_error(insert) or "")
    assert Program.objects.count() == 0
