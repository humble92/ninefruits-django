"""Original tests/Feature/Security/HardeningTest.php (security review 2026-10-23), the
authentication and authorization cases. The CSV formula and encrypted identifier case belongs
to reporting/people (Phase 2, Phase 11)."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError

from ninefruits.audit.models import SecurityEvent
from ninefruits.audit.security_events import SecurityEventType
from ninefruits.security.actions import AssignRole, UpdateUserAccount, UpdateUserPassword
from ninefruits.security.enums import MfaEnforcement, Permission, ScopeType
from tests.factories.security import RoleFactory, UserFactory
from tests.security.conftest import create_org_unit, signed_in

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mfa_not_used(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.DISABLED)


def _sessions_of(user_id: int) -> int:
    return sum(1 for s in Session.objects.all() if str(s.get_decoded().get("_auth_user_id")) == str(user_id))


def test_refuses_role_assignments_to_oneself_above_ones_own_permissions_or_outside_ones_scope() -> None:
    actor = UserFactory(
        permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.ROLE_ASSIGNMENTS_MANAGE, Permission.USERS_VIEW]
    )
    target = UserFactory()
    small = RoleFactory(permissions=[Permission.USERS_VIEW])
    big = RoleFactory(permissions=[Permission.USERS_VIEW, Permission.ROLES_MANAGE])

    with pytest.raises(ValidationError):
        AssignRole()(actor, small, "me", assigned_by=actor)
    with pytest.raises(ValidationError):
        AssignRole()(target, big, "escalation", assigned_by=actor)
    AssignRole()(target, small, "fine", assigned_by=actor)

    unit = create_org_unit()
    other = create_org_unit()
    dean = UserFactory(
        permissions=[Permission.ROLE_ASSIGNMENTS_MANAGE, Permission.USERS_VIEW],
        permissions__scope_type=ScopeType.ORG_UNIT,
        permissions__scope_id=unit,
    )

    with pytest.raises(ValidationError):
        AssignRole()(target, small, "global", assigned_by=dean)
    with pytest.raises(ValidationError):
        AssignRole()(target, small, "elsewhere", ScopeType.ORG_UNIT, other, assigned_by=dean)
    AssignRole()(target, small, "own unit", ScopeType.ORG_UNIT, unit, assigned_by=dean)


def test_resets_verification_ends_sessions_and_records_an_event_when_staff_change_an_email() -> None:
    admin = UserFactory(permissions=list(Permission))
    user = UserFactory()
    signed_in(user)
    assert _sessions_of(user.pk) == 1

    UpdateUserAccount()(user, {"email": "new@example.com", "is_active": True}, admin)

    user.refresh_from_db()
    assert user.email == "new@example.com"
    assert user.email_verified_at is None
    assert _sessions_of(user.pk) == 0
    assert SecurityEvent.objects.filter(type=SecurityEventType.EMAIL_CHANGED, user_id=user.pk).exists()


def test_stops_staff_deactivating_themselves_or_editing_a_more_privileged_account() -> None:
    admin = UserFactory(permissions=list(Permission))
    clerk = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.USERS_UPDATE])

    with pytest.raises(ValidationError):
        UpdateUserAccount()(admin, {"is_active": False}, admin)
    with pytest.raises(ValidationError):
        UpdateUserAccount()(admin, {"name": "Renamed"}, clerk)
    UpdateUserAccount()(clerk, {"name": "Renamed"}, admin)

    clerk.refresh_from_db()
    assert clerk.name == "Renamed"


def test_signs_a_deactivated_user_out_on_the_next_request() -> None:
    user = UserFactory()
    client = signed_in(user)

    assert client.get("/portal/").status_code == 200
    user.is_active = False
    user.save()

    response = client.get("/portal/")
    assert response.status_code == 302
    assert response["Location"] == "/accounts/login/"
    assert "_auth_user_id" not in client.session


def test_rotates_the_remember_token_ends_other_sessions_and_records_an_event_when_the_password_changes() -> None:
    user = UserFactory(password="Old-password-1!", remember_token="before")
    current = signed_in(user)
    signed_in(user)  # another browser
    assert _sessions_of(user.pk) == 2

    UpdateUserPassword()(
        user, "Old-password-1!", "New-password-1!", "New-password-1!", current_session_key=current.session.session_key
    )

    user.refresh_from_db()
    assert user.remember_token != "before"
    assert user.check_password("New-password-1!")
    assert _sessions_of(user.pk) == 1
    assert SecurityEvent.objects.filter(type=SecurityEventType.PASSWORD_CHANGED, user_id=user.pk).exists()


def test_refuses_a_password_change_with_a_wrong_current_password() -> None:
    user = UserFactory(password="Old-password-1!")

    with pytest.raises(ValidationError) as error:
        UpdateUserPassword()(user, "wrong", "New-password-1!", "New-password-1!")

    assert "current_password" in error.value.message_dict


def test_password_change_from_the_security_page_keeps_the_current_session() -> None:
    user = UserFactory(password="Old-password-1!")
    client = signed_in(user)

    response = client.post(
        "/portal/security/",
        {
            "action": "change_password",
            "current_password": "Old-password-1!",
            "password": "New-password-1!",
            "password_confirmation": "New-password-1!",
        },
    )

    assert response.context["password_changed"]
    assert client.get("/portal/").status_code == 200
