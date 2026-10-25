"""Original tests/Feature/Security/MfaPolicyTest.php."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta

import pytest
import time_machine
from django.utils import timezone

from ninefruits.security.actions import AssignRole
from ninefruits.security.enums import MfaEnforcement, Permission
from tests.factories.security import RoleFactory, UserFactory
from tests.security.conftest import signed_in

pytestmark = pytest.mark.django_db

RECOMMENDED = "We recommend enabling two-factor authentication for your account."
SECURITY_URL = "/portal/security/"


def test_only_reminds_users_when_two_factor_authentication_is_recommended(
    set_security_settings: Callable[..., None],
) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.RECOMMENDED)

    response = signed_in(UserFactory()).get("/portal/")

    assert response.status_code == 200
    assert RECOMMENDED in response.content.decode()


def test_shows_nothing_when_two_factor_authentication_is_not_used(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.DISABLED)

    response = signed_in(UserFactory()).get("/portal/")

    assert response.status_code == 200
    assert RECOMMENDED not in response.content.decode()


def test_lets_users_work_during_the_grace_period_and_then_requires_enrollment(
    set_security_settings: Callable[..., None],
) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.REQUIRED_FOR_ALL, mfa_grace_period_days=7)
    user = UserFactory()
    client = signed_in(user)

    assert client.get("/portal/").status_code == 200
    user.refresh_from_db()
    assert user.mfa_grace_started_at is not None

    with time_machine.travel(timezone.now() + timedelta(days=8)):
        client = signed_in(user)  # the earlier session has expired by then
        response = client.get("/portal/")
        assert response.status_code == 302
        assert response["Location"] == SECURITY_URL
        assert client.get(SECURITY_URL).status_code == 200


def test_applies_a_policy_change_on_the_next_request(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.RECOMMENDED, mfa_grace_period_days=0)
    client = signed_in(UserFactory())

    assert client.get("/portal/").status_code == 200

    set_security_settings(mfa_enforcement=MfaEnforcement.REQUIRED_FOR_ALL)

    assert client.get("/portal/")["Location"] == SECURITY_URL


def test_requires_two_factor_authentication_only_for_the_selected_roles(
    set_security_settings: Callable[..., None],
) -> None:
    role = RoleFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])
    set_security_settings(
        mfa_enforcement=MfaEnforcement.REQUIRED_FOR_ROLES, mfa_required_role_ids=[role.pk], mfa_grace_period_days=0
    )
    staff = UserFactory()
    AssignRole()(staff, role, "test")
    other = UserFactory()

    assert signed_in(staff).get("/portal/")["Location"] == SECURITY_URL
    assert signed_in(other).get("/portal/").status_code == 200


def test_blocks_the_admin_panel_until_enrollment(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.REQUIRED_FOR_ALL, mfa_grace_period_days=0)
    user = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])

    assert signed_in(user).get("/admin/")["Location"] == SECURITY_URL


def test_lets_enrolled_users_through(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.REQUIRED_FOR_ALL, mfa_grace_period_days=0)

    assert signed_in(UserFactory(with_mfa=True)).get("/portal/").status_code == 200


def test_answers_json_requests_with_403_until_enrollment(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.REQUIRED_FOR_ALL, mfa_grace_period_days=0)

    response = signed_in(UserFactory()).get("/portal/", headers={"Accept": "application/json"})

    assert response.status_code == 403


def test_still_allows_sign_out_and_password_confirmation(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.REQUIRED_FOR_ALL, mfa_grace_period_days=0)
    client = signed_in(UserFactory())

    assert client.get("/accounts/reauthenticate/").status_code == 200
    assert client.post("/accounts/logout/").status_code == 302
