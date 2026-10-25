"""``DJANGO_SECRET_KEY`` rotation (Phase 13, ``operations/security-keys.md``): with the previous
key in ``SECRET_KEY_FALLBACKS`` sessions, remembered devices and the secrets encrypted with a key
derived from ``SECRET_KEY`` keep working; ``security_reencrypt_secrets`` moves those secrets to the
current key so the previous one can be removed. The original rotated ``APP_KEY`` with
``APP_PREVIOUS_KEYS``."""

from __future__ import annotations

from collections.abc import Callable
from io import StringIO
from typing import Any

import pytest
from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import TOTP
from django.core.management import call_command
from django.test import Client, RequestFactory

from ninefruits.audit.models import ActivityLog
from ninefruits.security.crypto import decrypt_string, encrypt_string, reencrypt_string, uses_current_key
from ninefruits.security.enums import MfaEnforcement
from ninefruits.security.services.trusted_devices import COOKIE, TrustedDevices
from ninefruits.settings.groups.authentication import AuthenticationSettings
from tests.factories.security import UserFactory, current_otp, enroll_authenticator_app
from tests.security.conftest import signed_in

pytestmark = pytest.mark.django_db

OLD = "old-secret-key-for-rotation-tests-0123456789-abcdefghij"
NEW = "new-secret-key-for-rotation-tests-9876543210-jihgfedcba"


@pytest.fixture(autouse=True)
def _old_key(settings: Any, set_security_settings: Callable[..., None]) -> None:
    settings.SECRET_KEY = OLD
    settings.SECRET_KEY_FALLBACKS = []
    set_security_settings(mfa_enforcement=MfaEnforcement.DISABLED)


def _rotate(settings: Any, *, keep_previous: bool = True) -> None:
    settings.SECRET_KEY = NEW
    settings.SECRET_KEY_FALLBACKS = [OLD] if keep_previous else []


def _run(*args: str) -> str:
    out = StringIO()
    status = call_command("security_reencrypt_secrets", *args, stdout=out, stderr=out)
    assert status == 0, out.getvalue()
    return out.getvalue()


def test_reads_secrets_written_with_a_fallback_key_and_moves_them_to_the_current_key(settings: Any) -> None:
    value = encrypt_string("totp-secret")
    _rotate(settings)

    assert decrypt_string(value) == "totp-secret"
    assert not uses_current_key(value)
    moved = reencrypt_string(value)
    assert uses_current_key(moved)
    assert reencrypt_string(moved) == moved

    _rotate(settings, keep_previous=False)
    assert decrypt_string(moved) == "totp-secret"
    with pytest.raises(ValueError):
        decrypt_string(value)


def test_keeps_people_signed_in_while_the_previous_key_is_a_fallback(settings: Any) -> None:
    active, away = signed_in(UserFactory()), signed_in(UserFactory())

    _rotate(settings)
    # Django moves a session to the current key on its first request after the rotation.
    assert active.get("/portal/").status_code == 200

    _rotate(settings, keep_previous=False)
    assert active.get("/portal/").status_code == 200
    assert away.get("/portal/").status_code == 302


def test_trusts_remembered_devices_signed_with_the_previous_key_until_it_is_removed(
    settings: Any, set_security_settings: Callable[..., None]
) -> None:
    set_security_settings(mfa_remember_device_days=30)
    user = UserFactory(with_mfa=True)
    response = Client().get("/accounts/login/")
    TrustedDevices().remember(response, user)
    request = RequestFactory().get("/")
    request.COOKIES[COOKIE] = response.cookies[COOKIE].value

    _rotate(settings)
    assert TrustedDevices().is_trusted(request, user)

    _rotate(settings, keep_previous=False)
    assert not TrustedDevices().is_trusted(request, user)


def test_reencrypts_authenticator_and_sso_secrets_with_the_current_key(
    settings: Any, set_authentication_settings: Callable[..., None]
) -> None:
    user = UserFactory()
    codes = enroll_authenticator_app(user)
    set_authentication_settings(
        sso_providers=[
            {
                "key": "school",
                "label": "School account",
                "issuer": "https://idp.example.test",
                "client_id": "sis",
                "client_secret": encrypt_string("client-secret"),
                "scopes": "openid email",
                "trusts_mfa": False,
                "is_enabled": True,
            }
        ]
    )
    _rotate(settings)

    assert "Dry run: 2 authenticator(s) and 1 SSO client secret(s) use a previous key." in _run("--dry-run")
    assert "2 authenticator(s) and 1 SSO client secret(s) re-encrypted." in _run()
    assert "Dry run: 0 authenticator(s) and 0 SSO client secret(s)" in _run("--dry-run")
    entry = ActivityLog.objects.filter(event="command.executed").order_by("-id").first()
    assert entry is not None and entry.properties["command"] == "security_reencrypt_secrets"

    # Without the previous key everything still works.
    _rotate(settings, keep_previous=False)
    totp = Authenticator.objects.get(user=user, type=Authenticator.Type.TOTP)
    assert TOTP(totp).validate_code(current_otp())
    recovery = Authenticator.objects.get(user=user, type=Authenticator.Type.RECOVERY_CODES)
    assert RecoveryCodes(recovery).generate_codes() == codes
    provider = AuthenticationSettings.load().sso_providers[0]
    assert decrypt_string(provider["client_secret"]) == "client-secret"


def test_reports_secrets_no_configured_key_can_read(settings: Any) -> None:
    enroll_authenticator_app(UserFactory())
    _rotate(settings, keep_previous=False)

    out = StringIO()
    status = call_command("security_reencrypt_secrets", stdout=out, stderr=out)

    assert status == 1
    assert "cannot be decrypted" in out.getvalue()
