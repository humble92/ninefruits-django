"""Security and sign-in settings pages (original ManageSecuritySettings and
ManageAuthenticationSettings; cases from tests/Feature/Admin/AdminPanelTest.php and the
"security settings" entry of AdminPagesTest.php)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from ninefruits.audit.models import ActivityLog
from ninefruits.security.crypto import decrypt_string
from ninefruits.security.enums import MfaEnforcement, Permission, SsoLinkMode, StudentNumberLogin
from ninefruits.settings.groups.authentication import AuthenticationSettings
from ninefruits.settings.groups.security import SecuritySettings
from tests.factories.security import RoleFactory, UserFactory
from tests.security.conftest import signed_in

pytestmark = pytest.mark.django_db

SECURITY_URL = "/admin/settings/security/"
AUTHENTICATION_URL = "/admin/settings/authentication/"


@pytest.fixture(autouse=True)
def _mfa_not_used(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.DISABLED)


def administrator():  # type: ignore[no-untyped-def]
    return UserFactory(permissions=list(Permission))


def provider_row(index: int, **values: str) -> dict[str, str]:
    return {f"sso_providers-{index}-{name}": value for name, value in values.items()}


@pytest.mark.parametrize("url", [SECURITY_URL, AUTHENTICATION_URL])
def test_renders_the_settings_pages(url: str) -> None:
    response = signed_in(administrator()).get(url)

    assert response.status_code == 200


def test_changes_the_two_factor_policy_from_the_security_settings_page() -> None:
    role = RoleFactory()

    response = signed_in(administrator()).post(
        SECURITY_URL,
        {
            "mfa_enforcement": MfaEnforcement.REQUIRED_FOR_ROLES.value,
            "mfa_required_role_ids": [str(role.pk)],
            "mfa_grace_period_days": "3",
            "mfa_remember_device_days": "0",
        },
    )

    assert response.status_code == 302
    settings = SecuritySettings.load()
    assert settings.mfa_enforcement == MfaEnforcement.REQUIRED_FOR_ROLES
    assert settings.mfa_required_role_ids == [role.pk]
    assert settings.mfa_grace_period_days == 3
    assert settings.mfa_email_code_enabled is False
    assert ActivityLog.objects.filter(event="settings.updated").exists()


def test_validates_the_security_settings() -> None:
    client = signed_in(administrator())
    data = {"mfa_grace_period_days": "91", "mfa_remember_device_days": "0"}

    response = client.post(SECURITY_URL, {"mfa_enforcement": MfaEnforcement.REQUIRED_FOR_ROLES.value, **data})

    assert response.status_code == 422
    errors = response.context["form"].errors
    assert "mfa_grace_period_days" in errors and "mfa_required_role_ids" in errors
    assert SecuritySettings.load().mfa_enforcement == MfaEnforcement.DISABLED


def test_drops_required_roles_unless_the_policy_uses_them() -> None:
    role = RoleFactory()

    signed_in(administrator()).post(
        SECURITY_URL,
        {
            "mfa_enforcement": MfaEnforcement.REQUIRED_FOR_ALL.value,
            "mfa_required_role_ids": [str(role.pk)],
            "mfa_grace_period_days": "0",
            "mfa_remember_device_days": "30",
            "mfa_email_code_enabled": "on",
        },
    )

    settings = SecuritySettings.load()
    assert settings.mfa_required_role_ids == []
    assert settings.mfa_email_code_enabled is True


@pytest.mark.parametrize(
    ("permission", "url"),
    [
        (Permission.SECURITY_SETTINGS_MANAGE, SECURITY_URL),
        (Permission.AUTHENTICATION_SETTINGS_MANAGE, AUTHENTICATION_URL),
    ],
)
def test_hides_the_settings_pages_without_permission(permission: Permission, url: str) -> None:
    user = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])
    assert signed_in(user).get(url).status_code == 403

    allowed = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, permission])
    assert signed_in(allowed).get(url).status_code == 200


def _authentication_data(**extra: str) -> dict[str, str]:
    return {
        "student_number_login": StudentNumberLogin.ACTIVE_RECORDS.value,
        "password_login_for_sso_users": "on",
        "lockout_threshold": "5",
        "lockout_minutes": "30",
        "sso_link_mode": SsoLinkMode.INSTITUTIONAL_EMAIL.value,
        **extra,
    }


def test_saves_sign_in_methods_and_keeps_client_secrets_encrypted_and_hidden() -> None:
    client = signed_in(administrator())
    row = provider_row(
        0,
        key="school",
        label="School account",
        issuer="https://idp.example.test/",
        client_id="sis-client",
        client_secret="top-secret",
        scopes="openid email",
        is_enabled="1",
    )

    response = client.post(AUTHENTICATION_URL, _authentication_data(**row))

    assert response.status_code == 302
    settings = AuthenticationSettings.load()
    assert settings.student_number_login == StudentNumberLogin.ACTIVE_RECORDS
    assert settings.lockout_threshold == 5 and settings.lockout_minutes == 30
    provider = settings.sso_providers[0]
    assert provider["issuer"] == "https://idp.example.test"
    assert provider["client_secret"] != "top-secret"
    assert decrypt_string(provider["client_secret"]) == "top-secret"
    assert "top-secret" not in client.get(AUTHENTICATION_URL).content.decode()

    # An empty secret keeps the stored one.
    row = provider_row(0, key="school", label="School", issuer="https://idp.example.test", client_id="sis-client")
    client.post(AUTHENTICATION_URL, _authentication_data(**row))
    provider = AuthenticationSettings.load().sso_providers[0]
    assert provider["label"] == "School"
    assert decrypt_string(provider["client_secret"]) == "top-secret"
    assert provider["is_enabled"] is False

    # Removing a provider.
    client.post(AUTHENTICATION_URL, _authentication_data(**row, **{"sso_providers-0-delete": "1"}))
    assert AuthenticationSettings.load().sso_providers == []


def test_validates_providers_and_limits() -> None:
    row = provider_row(0, key="Bad Key", label="", issuer="not a url", client_id="")

    response = signed_in(administrator()).post(AUTHENTICATION_URL, _authentication_data(lockout_minutes="0", **row))

    assert response.status_code == 422
    errors = response.context["form"].errors
    assert "sso_providers" in errors and "lockout_minutes" in errors
    assert len(errors["sso_providers"]) == 4
