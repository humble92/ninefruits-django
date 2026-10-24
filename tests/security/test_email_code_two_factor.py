"""Original tests/Feature/Security/EmailCodeTwoFactorTest.php. The Livewire component calls
are POSTs to the portal security page (``action=...``)."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import timedelta

import pytest
import time_machine
from django.core import mail
from django.test import Client
from django.utils import timezone

from ninefruits.audit.models import SecurityEvent
from ninefruits.audit.security_events import SecurityEventType
from ninefruits.security.actions import ResetUserMfa
from ninefruits.security.enums import MfaEnforcement
from ninefruits.security.models import User
from ninefruits.security.services.email_code import PURPOSE_ENROLLMENT, PURPOSE_LOGIN, EmailCodeChallenge
from tests.factories.security import PASSWORD, UserFactory, has_authenticator_app
from tests.security.conftest import confirm_password, signed_in

pytestmark = pytest.mark.django_db

CHALLENGE = "/accounts/2fa/challenge/"
SECURITY_URL = "/portal/security/"


@pytest.fixture(autouse=True)
def _email_codes_allowed(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.RECOMMENDED, mfa_email_code_enabled=True)


def last_email_code(user: User) -> str:
    messages = [message for message in mail.outbox if user.email in message.to]
    assert messages, "no code was sent"
    match = re.search(r"^(\d{6})$", messages[-1].body, re.MULTILINE)
    assert match
    return match.group(1)


def sign_in_with_password(client: Client, user: User) -> str:
    return str(client.post("/accounts/login/", {"login": user.email, "password": PASSWORD})["Location"])


def now() -> timezone.datetime:
    return timezone.now().replace(microsecond=0)


def test_sends_a_code_and_asks_for_it_when_email_is_the_only_method() -> None:
    user = UserFactory(email_mfa_enabled_at=now())
    client = Client()

    assert sign_in_with_password(client, user) == CHALLENGE
    assert "_auth_user_id" not in client.session
    assert "Enter the 6-digit code we sent to your email." in client.get(CHALLENGE).content.decode()

    response = client.post("/accounts/2fa/challenge/email/", {"email_code": last_email_code(user)})

    assert response["Location"] == "/portal/"
    assert int(client.session["_auth_user_id"]) == user.pk
    assert SecurityEvent.objects.filter(type=SecurityEventType.MFA_EMAIL_CODE_SENT).exists()


def test_rejects_a_wrong_code_and_records_the_failure() -> None:
    user = UserFactory(email_mfa_enabled_at=now())
    client = Client()
    sign_in_with_password(client, user)

    response = client.post("/accounts/2fa/challenge/email/", {"email_code": "000000"})

    assert response.status_code == 200
    assert response.context["email_error"]
    assert "_auth_user_id" not in client.session
    assert SecurityEvent.objects.filter(type=SecurityEventType.MFA_CHALLENGE_FAILED, user_id=user.pk).exists()


def test_discards_the_code_after_too_many_wrong_attempts() -> None:
    user = UserFactory(email_mfa_enabled_at=now())
    challenge = EmailCodeChallenge()
    challenge.send(user, PURPOSE_LOGIN)
    code = last_email_code(user)

    for _attempt in range(EmailCodeChallenge.MAX_ATTEMPTS):
        assert not challenge.verify(user, PURPOSE_LOGIN, "999999")

    assert not challenge.verify(user, PURPOSE_LOGIN, code)


def test_accepts_a_code_once_and_only_before_it_expires() -> None:
    user = UserFactory()
    challenge = EmailCodeChallenge()
    start = timezone.now()

    challenge.send(user, PURPOSE_LOGIN)
    code = last_email_code(user)

    assert challenge.verify(user, PURPOSE_LOGIN, code)
    assert not challenge.verify(user, PURPOSE_LOGIN, code)

    with time_machine.travel(start + timedelta(minutes=2)):
        challenge.send(user, PURPOSE_LOGIN)
        second = last_email_code(user)

    with time_machine.travel(start + timedelta(minutes=2 + EmailCodeChallenge.CODE_LIFETIME_MINUTES + 1)):
        assert not challenge.verify(user, PURPOSE_LOGIN, second)


def test_does_not_accept_a_code_issued_for_another_purpose() -> None:
    user = UserFactory()
    challenge = EmailCodeChallenge()
    challenge.send(user, PURPOSE_ENROLLMENT)

    assert not challenge.verify(user, PURPOSE_LOGIN, last_email_code(user))


def test_limits_how_often_codes_are_sent() -> None:
    user = UserFactory()
    challenge = EmailCodeChallenge()
    start = timezone.now()

    assert challenge.send(user, PURPOSE_LOGIN)
    assert not challenge.send(user, PURPOSE_LOGIN)

    elapsed = 0
    for _send in range(2, EmailCodeChallenge.SENDS_PER_HOUR + 1):
        elapsed += EmailCodeChallenge.RESEND_AFTER_SECONDS + 1
        with time_machine.travel(start + timedelta(seconds=elapsed)):
            assert challenge.send(user, PURPOSE_LOGIN)

    elapsed += EmailCodeChallenge.RESEND_AFTER_SECONDS + 1
    with time_machine.travel(start + timedelta(seconds=elapsed)):
        assert not challenge.send(user, PURPOSE_LOGIN)


def test_does_not_offer_email_codes_to_users_who_only_use_an_authenticator_app() -> None:
    user = UserFactory(with_mfa=True)
    client = Client()
    assert sign_in_with_password(client, user) == CHALLENGE

    assert client.post("/accounts/2fa/challenge/email/send/").status_code == 403
    assert mail.outbox == []


def test_stops_counting_email_codes_when_the_institution_turns_them_off(
    set_security_settings: Callable[..., None],
) -> None:
    user = UserFactory(email_mfa_enabled_at=now())
    set_security_settings(mfa_email_code_enabled=False)

    assert sign_in_with_password(Client(), user) == "/portal/"
    assert mail.outbox == []


def test_satisfies_a_required_policy_with_email_codes(set_security_settings: Callable[..., None]) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.REQUIRED_FOR_ALL, mfa_grace_period_days=0)

    assert signed_in(UserFactory(email_mfa_enabled_at=now())).get("/portal/").status_code == 200


def test_enrolls_email_codes_from_the_security_page_after_password_confirmation() -> None:
    user = UserFactory()
    client = signed_in(user)

    response = client.post(SECURITY_URL, {"action": "send_email_code"})
    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/reauthenticate/")

    confirm_password(client)

    response = client.post(SECURITY_URL, {"action": "send_email_code"})
    assert response.status_code == 200
    assert response.context["errors"] == {}
    assert response.context["email_code_sent"]

    response = client.post(SECURITY_URL, {"action": "confirm_email", "email_code": last_email_code(user)})

    assert response.context["errors"] == {}
    user.refresh_from_db()
    assert user.email_mfa_enabled_at is not None
    assert SecurityEvent.objects.filter(type=SecurityEventType.MFA_EMAIL_ENABLED).exists()


def test_keeps_at_least_one_method_when_two_factor_authentication_is_required(
    set_security_settings: Callable[..., None],
) -> None:
    set_security_settings(mfa_enforcement=MfaEnforcement.REQUIRED_FOR_ALL)
    user = UserFactory(with_mfa=True, email_mfa_enabled_at=now())
    client = signed_in(user)
    confirm_password(client)

    assert client.post(SECURITY_URL, {"action": "disable_email"}).context["errors"] == {}
    user.refresh_from_db()
    assert user.email_mfa_enabled_at is None

    assert "disable" in client.post(SECURITY_URL, {"action": "disable"}).context["errors"]
    assert has_authenticator_app(user)


def test_is_cleared_by_an_administrator_reset() -> None:
    user = UserFactory(email_mfa_enabled_at=now())

    ResetUserMfa()(user, "Lost mailbox access", UserFactory())

    user.refresh_from_db()
    assert user.email_mfa_enabled_at is None


@pytest.mark.parametrize(
    "action", ["enable", "disable", "regenerate_recovery_codes", "send_email_code", "disable_email"]
)
def test_changes_nothing_until_the_password_is_confirmed(action: str) -> None:
    user = UserFactory(with_mfa=True)

    response = signed_in(user).post(SECURITY_URL, {"action": action})

    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/reauthenticate/")
    user.refresh_from_db()
    assert has_authenticator_app(user)
    assert user.email_mfa_enabled_at is None
    assert mail.outbox == []
