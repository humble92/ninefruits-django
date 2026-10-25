"""Admin screens for users, roles and assignments (original Filament Users/Roles resources;
cases from tests/Feature/Admin/AdminPanelTest.php about these resources)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone

from ninefruits.audit.models import ActivityLog
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.security.models import Role, RoleAssignment, User
from tests.factories.security import RoleFactory, UserFactory, has_authenticator_app
from tests.security.conftest import signed_in

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mfa_not_used(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.DISABLED)


def administrator() -> User:
    return UserFactory(permissions=list(Permission))


def test_lists_users_and_creates_an_account_with_a_reset_link() -> None:
    client = signed_in(administrator())
    UserFactory(name="Listed Person")

    assert "Listed Person" in client.get("/admin/security/user/").content.decode()

    response = client.post(
        "/admin/security/user/add/", {"name": "New Staff", "email": "New@Example.test", "locale": ""}
    )

    assert response.status_code == 302, response.context["adminform"].form.errors
    user = User.objects.get(email="new@example.test")
    assert user.has_usable_password()
    assert any("new@example.test" in message.to for message in mail.outbox)


def test_edits_go_through_update_user_account() -> None:
    admin = administrator()
    user = UserFactory()
    client = signed_in(admin)

    response = client.post(
        f"/admin/security/user/{user.pk}/change/",
        {
            "name": user.name,
            "email": "changed@example.test",
            "locale": "",
            "is_active": "on",
            "role_assignments-TOTAL_FORMS": "0",
            "role_assignments-INITIAL_FORMS": "0",
        },
    )

    assert response.status_code == 302, response.context["adminform"].form.errors if response.context else ""
    user.refresh_from_db()
    assert user.email == "changed@example.test"
    assert user.email_verified_at is None
    assert ActivityLog.objects.filter(event="user.email_changed").exists()


def test_cannot_edit_a_more_privileged_account() -> None:
    clerk = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.USERS_VIEW, Permission.USERS_UPDATE])
    admin = administrator()

    response = signed_in(clerk).post(
        f"/admin/security/user/{admin.pk}/change/",
        {
            "name": "Renamed",
            "email": admin.email,
            "locale": "",
            "is_active": "on",
            "role_assignments-TOTAL_FORMS": "0",
            "role_assignments-INITIAL_FORMS": "0",
        },
    )

    assert response.status_code == 200
    admin.refresh_from_db()
    assert admin.name != "Renamed"


def test_users_are_never_deleted() -> None:
    client = signed_in(administrator())
    user = UserFactory()

    assert client.post(f"/admin/security/user/{user.pk}/delete/", {"post": "yes"}).status_code == 403


def test_resets_two_factor_authentication_with_a_reason() -> None:
    admin = administrator()
    user = UserFactory(with_mfa=True)
    client = signed_in(admin)
    url = f"/admin/security/user/{user.pk}/reset-mfa/"

    client.post(url, {"_form_submitted": "1"})
    assert has_authenticator_app(user)

    response = client.post(url, {"_form_submitted": "1", "reason": "Lost phone"})

    assert response.status_code == 302
    assert not has_authenticator_app(user)
    assert ActivityLog.objects.get(event="mfa.reset").reason == "Lost phone"


def test_cannot_reset_own_two_factor_authentication() -> None:
    admin = administrator()

    response = signed_in(admin).post(
        f"/admin/security/user/{admin.pk}/reset-mfa/", {"_form_submitted": "1", "reason": "x"}
    )

    assert response.status_code == 403


def test_unlocks_an_account_with_a_reason() -> None:
    user = UserFactory(locked_until=timezone.now() + timedelta(hours=1), failed_login_count=2)

    signed_in(administrator()).post(
        f"/admin/security/user/{user.pk}/unlock/", {"_form_submitted": "1", "reason": "Help desk call"}
    )

    user.refresh_from_db()
    assert not user.is_locked()


def test_assigns_and_ends_roles() -> None:
    admin = administrator()
    user = UserFactory()
    role = RoleFactory(permissions=[Permission.USERS_VIEW])
    client = signed_in(admin)

    response = client.post(
        f"/admin/security/user/{user.pk}/assign-role/",
        {"role": role.pk, "scope_type": "global", "reason": "Covering"},
    )

    assert response.status_code == 302
    assignment = RoleAssignment.objects.get(user=user)
    assert assignment.reason == "Covering"
    assert assignment.assigned_by == admin
    assert "End assignment" in client.get(f"/admin/security/user/{user.pk}/change/").content.decode()

    url = f"/admin/security/user/{user.pk}/assignments/{assignment.pk}/revoke/"
    assert client.post(url, {"reason": "Back to normal"}).status_code == 302

    assignment.refresh_from_db()
    assert not assignment.is_active()


def test_cannot_end_own_assignment() -> None:
    admin = administrator()
    own = admin.role_assignments.get()

    response = signed_in(admin).post(f"/admin/security/user/{admin.pk}/assignments/{own.pk}/revoke/", {"reason": "x"})

    assert response.status_code == 403


def test_creates_a_role_with_permissions_and_audits_them() -> None:
    client = signed_in(administrator())

    response = client.post(
        "/admin/security/role/add/",
        {
            "name": "records_clerk",
            "display_name__en": "Records clerk",
            "display_name__ko": "학적 사무",
            "permissions__users": [Permission.USERS_VIEW.value],
            "permissions__roles": [Permission.ROLES_VIEW.value],
        },
    )

    assert response.status_code == 302, response.context["adminform"].form.errors if response.context else ""
    role = Role.objects.get(name="records_clerk")
    assert role.display_name_translations == {"en": "Records clerk", "ko": "학적 사무"}
    assert role.permission_names() == [Permission.ROLES_VIEW.value, Permission.USERS_VIEW.value]
    assert ActivityLog.objects.filter(event="role.permissions_changed", subject_id=role.pk).exists()


def test_refuses_invalid_role_names_and_protects_system_roles() -> None:
    client = signed_in(administrator())

    response = client.post("/admin/security/role/add/", {"name": "Bad Name", "display_name__en": "Bad"})
    assert response.status_code == 200
    assert not Role.objects.filter(display_name__en="Bad").exists()

    system = RoleFactory(is_system=True)
    assert client.post(f"/admin/security/role/{system.pk}/delete/", {"post": "yes"}).status_code == 403
    persona = RoleFactory(name="student", persona_of="student")
    assert client.post(f"/admin/security/role/{persona.pk}/delete/", {"post": "yes"}).status_code == 403
    unused = RoleFactory()
    assert client.post(f"/admin/security/role/{unused.pk}/delete/", {"post": "yes"}).status_code == 302
    assert not Role.objects.filter(pk=unused.pk).exists()
