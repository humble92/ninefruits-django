"""Original tests/Feature/Security/AuthorizationTest.php."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import timedelta

import pytest
import time_machine
from django.core.exceptions import ValidationError
from django.test import Client
from django.utils import timezone

from ninefruits.audit.models import ActivityLog
from ninefruits.security.actions import AssignRole, RevokeRoleAssignment
from ninefruits.security.enums import MfaEnforcement, Permission, Persona, ScopeType
from ninefruits.security.models import User
from ninefruits.security.services.authorization import authorization
from ninefruits.security.services.personas import PersonaResolver, use_resolver
from tests.factories.security import RoleFactory, UserFactory
from tests.security.conftest import create_org_unit, create_program, signed_in

pytestmark = pytest.mark.django_db

USERS_URL = "/admin/security/user/"
ROLES_URL = "/admin/security/role/"


@pytest.fixture(autouse=True)
def _mfa_not_used(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.DISABLED)


def test_denies_the_admin_panel_without_a_role() -> None:
    assert signed_in(UserFactory()).get("/admin/").status_code == 403


def test_grants_and_removes_access_by_changing_role_assignments_only() -> None:
    user = UserFactory()
    admin = UserFactory(permissions=list(Permission))
    role = RoleFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.USERS_VIEW])

    assignment = AssignRole()(user, role, "New registrar", assigned_by=admin)

    client = signed_in(user)
    assert client.get("/admin/").status_code == 200
    assert client.get(USERS_URL).status_code == 200
    assert client.get(ROLES_URL).status_code == 403

    RevokeRoleAssignment()(assignment, "Left the office", admin)

    assert client.get("/admin/").status_code == 403


def test_opens_a_page_as_soon_as_the_role_gains_the_permission() -> None:
    user = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])
    client = signed_in(user)

    assert client.get(ROLES_URL).status_code == 403

    role = user.role_assignments.get().role
    role.give_permission_to(Permission.ROLES_VIEW)
    authorization().flush()

    assert client.get(ROLES_URL).status_code == 200


@pytest.mark.parametrize(("extra", "sees_roles"), [([], False), ([Permission.ROLES_VIEW], True)])
def test_shows_only_the_menu_entries_the_user_is_allowed_to_use(extra: list[Permission], sees_roles: bool) -> None:
    user = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, *extra])

    response = signed_in(user).get("/admin/")

    assert response.status_code == 200
    assert (ROLES_URL in response.content.decode()) is sees_roles


def test_ignores_assignments_outside_their_validity_period() -> None:
    user = UserFactory()
    role = RoleFactory(permissions=[Permission.USERS_VIEW])
    now = timezone.now()

    AssignRole()(user, role, "future", starts_at=now + timedelta(days=1))
    AssignRole()(user, role, "expired", starts_at=now - timedelta(days=10), ends_at=now - timedelta(days=1))

    assert not authorization().has_permission(user, Permission.USERS_VIEW)

    with time_machine.travel(now + timedelta(days=2)):
        authorization().flush()
        assert authorization().has_permission(user, Permission.USERS_VIEW)


def test_merges_scopes_from_several_assignments_and_includes_units_below_an_org_unit() -> None:
    user = UserFactory()
    role = RoleFactory(permissions=[Permission.USERS_VIEW])
    college = create_org_unit()
    department = create_org_unit(parent_id=college)
    other = create_org_unit()
    program = create_program()

    AssignRole()(user, role, "college", ScopeType.ORG_UNIT, college)
    AssignRole()(user, role, "other unit", ScopeType.ORG_UNIT, other)
    AssignRole()(user, role, "program", ScopeType.PROGRAM, program)

    scope = authorization().scope_for(user, Permission.USERS_VIEW)

    assert not scope.is_global
    assert sorted(scope.org_unit_ids) == sorted([college, department, other])
    assert scope.program_ids == (program,)


def test_gives_deactivated_users_no_permissions() -> None:
    user = UserFactory(permissions=[Permission.USERS_VIEW])
    user.is_active = False
    user.save()
    authorization().flush()

    assert not user.has_perm(Permission.USERS_VIEW)


class _StudentDetector:
    persona = Persona.STUDENT

    def applies_to(self, user: User) -> bool:
        return user.email == "student@example.com"


@pytest.fixture
def student_detector() -> Iterator[None]:
    use_resolver(PersonaResolver([_StudentDetector()]))
    yield
    use_resolver(None)


def test_grants_persona_permissions_from_data_limited_to_own_records(student_detector: None) -> None:
    RoleFactory.persona_role(Persona.STUDENT, permissions=[Permission.USERS_VIEW])
    student = UserFactory(email="student@example.com")

    scope = authorization().scope_for(student, Permission.USERS_VIEW)

    assert scope.includes_own
    assert not scope.is_global
    assert not authorization().has_permission(UserFactory(), Permission.USERS_VIEW)


def test_does_not_allow_assigning_persona_roles_by_hand() -> None:
    role = RoleFactory.persona_role(Persona.STUDENT)

    with pytest.raises(ValidationError):
        AssignRole()(UserFactory(), role, "manual")


def test_audits_role_assignments_with_the_reason() -> None:
    admin = UserFactory(permissions=list(Permission))
    role = RoleFactory()

    assignment = AssignRole()(UserFactory(), role, "Covering for a colleague", assigned_by=admin)

    activity = ActivityLog.objects.get(event="role.assigned", subject_id=assignment.pk)
    assert activity.reason == "Covering for a colleague"
    assert activity.causer_id == admin.pk


def test_stops_users_from_ending_their_own_assignments() -> None:
    admin = UserFactory(permissions=[Permission.ROLE_ASSIGNMENTS_MANAGE])
    own = admin.role_assignments.get()

    assert not admin.has_perm("revoke", own)


def test_guests_are_sent_to_the_shared_sign_in_from_the_admin() -> None:
    response = Client().get("/admin/")

    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")
