"""Portal security page (original Livewire SecuritySettings): authenticator app enrollment with
recovery codes, sign-in with a recovery code, HTMX partials and SSO unlinking."""

from __future__ import annotations

import pytest
from allauth.mfa.totp.internal.auth import format_hotp_value, hotp_value, yield_hotp_counters_from_time
from django.test import Client

from ninefruits.audit.models import ActivityLog, SecurityEvent
from ninefruits.audit.security_events import SecurityEventType
from ninefruits.portal.views.security import PENDING_SECRET_KEY
from ninefruits.security.models import UserIdentity
from tests.factories.security import PASSWORD, UserFactory, enroll_authenticator_app, has_authenticator_app
from tests.security.conftest import confirm_password, signed_in

pytestmark = pytest.mark.django_db

URL = "/portal/security/"


def otp(secret: str) -> str:
    return format_hotp_value(hotp_value(secret, next(iter(yield_hotp_counters_from_time()))))


def test_shows_the_page() -> None:
    response = signed_in(UserFactory()).get(URL)

    assert response.status_code == 200
    assert "Enable two-factor authentication" in response.content.decode()


def test_enrolls_an_authenticator_app_and_shows_recovery_codes() -> None:
    user = UserFactory()
    client = signed_in(user)
    confirm_password(client)

    response = client.post(URL, {"action": "enable"})
    assert response.context["pending"]
    assert "<svg" in response.content.decode()
    secret = client.session[PENDING_SECRET_KEY]

    response = client.post(URL, {"action": "confirm", "code": "000000"})
    assert "code" in response.context["errors"]
    assert not has_authenticator_app(user)

    response = client.post(URL, {"action": "confirm", "code": otp(secret)})

    assert response.context["errors"] == {}
    assert len(response.context["recovery_codes"]) == 10
    assert has_authenticator_app(user)
    types = set(SecurityEvent.objects.filter(user_id=user.pk).values_list("type", flat=True))
    assert {SecurityEventType.MFA_ENABLED.value, SecurityEventType.MFA_CONFIRMED.value} <= types


def test_htmx_requests_get_the_changed_section_only() -> None:
    client = signed_in(UserFactory())
    confirm_password(client)

    response = client.post(URL, {"action": "enable"}, headers={"HX-Request": "true"})

    body = response.content.decode()
    assert body.lstrip().startswith('<section id="section-authenticator"')
    assert "<html" not in body


def test_htmx_requests_are_sent_to_the_password_confirmation() -> None:
    response = signed_in(UserFactory()).post(URL, {"action": "enable"}, headers={"HX-Request": "true"})

    assert response.status_code == 204
    assert response["HX-Redirect"].startswith("/accounts/reauthenticate/")


def test_regenerates_recovery_codes_and_signs_in_with_one() -> None:
    user = UserFactory()
    old_codes = enroll_authenticator_app(user)
    client = signed_in(user)
    confirm_password(client)

    codes = client.post(URL, {"action": "regenerate_recovery_codes"}).context["recovery_codes"]
    assert codes and codes != old_codes

    guest = Client()
    guest.post("/accounts/login/", {"login": user.email, "password": PASSWORD})
    response = guest.post("/accounts/2fa/challenge/", {"recovery_code": codes[0]})

    assert response["Location"] == "/portal/"
    assert SecurityEvent.objects.filter(type=SecurityEventType.MFA_RECOVERY_CODE_USED, user_id=user.pk).exists()


def test_records_a_rejected_authenticator_code() -> None:
    user = UserFactory(with_mfa=True)
    client = Client()
    client.post("/accounts/login/", {"login": user.email, "password": PASSWORD})

    response = client.post("/accounts/2fa/challenge/", {"code": "000000"})

    assert response.status_code == 200
    assert "_auth_user_id" not in client.session
    assert SecurityEvent.objects.filter(type=SecurityEventType.MFA_CHALLENGE_FAILED, user_id=user.pk).exists()


def test_disables_the_authenticator_app() -> None:
    user = UserFactory(with_mfa=True)
    client = signed_in(user)
    confirm_password(client)

    client.post(URL, {"action": "disable"})

    assert not has_authenticator_app(user)
    assert SecurityEvent.objects.filter(type=SecurityEventType.MFA_DISABLED, user_id=user.pk).exists()


def test_unlinks_only_own_school_accounts() -> None:
    user = UserFactory()
    other = UserFactory()
    own = UserIdentity.objects.create(user=user, provider="school", subject="a")
    foreign = UserIdentity.objects.create(user=other, provider="school", subject="b")
    client = signed_in(user)
    confirm_password(client)

    assert client.post(URL, {"action": "unlink_identity", "identity_id": foreign.pk}).status_code == 404
    client.post(URL, {"action": "unlink_identity", "identity_id": own.pk})

    assert not UserIdentity.objects.filter(pk=own.pk).exists()
    assert UserIdentity.objects.filter(pk=foreign.pk).exists()
    assert ActivityLog.objects.filter(event="sso.unlinked").exists()


def test_allauth_mfa_pages_lead_to_the_security_page() -> None:
    client = signed_in(UserFactory())

    assert client.get("/accounts/2fa/")["Location"] == URL
    assert client.get("/accounts/2fa/totp/activate/")["Location"] == URL
