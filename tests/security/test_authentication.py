"""Original tests/Feature/Security/AuthenticationTest.php."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from django.db import connection
from django.test import Client, RequestFactory
from django.utils import timezone

from ninefruits.audit.models import SecurityEvent
from ninefruits.audit.security_events import SecurityEventType
from ninefruits.security.services.trusted_devices import COOKIE, TrustedDevices
from tests.factories.security import PASSWORD, UserFactory, current_otp

pytestmark = pytest.mark.django_db

LOGIN = "/accounts/login/"
CHALLENGE = "/accounts/2fa/challenge/"


def sign_in(client: Client, login: str, password: str = PASSWORD) -> Any:
    return client.post(LOGIN, {"login": login, "password": password})


def test_signs_in_with_valid_credentials_and_records_the_event() -> None:
    user = UserFactory()
    client = Client()

    response = sign_in(client, user.email)

    assert response.status_code == 302
    assert response["Location"] == "/portal/"
    assert int(client.session["_auth_user_id"]) == user.pk
    assert SecurityEvent.objects.filter(type=SecurityEventType.LOGIN_SUCCEEDED, user_id=user.pk).exists()
    user.refresh_from_db()
    assert user.last_login is not None


def test_attributes_changes_made_during_sign_in_to_the_user() -> None:
    user = UserFactory()

    sign_in(Client(), user.email)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT changed_columns, actor FROM audit.record_changes "
            "WHERE table_name = 'users' AND operation = 'UPDATE' ORDER BY id DESC LIMIT 1"
        )
        changed_columns, actor = cursor.fetchone()
    assert "last_login_at" in changed_columns
    assert actor == f"user:{user.pk}"


def test_rejects_invalid_credentials_and_records_the_failure() -> None:
    user = UserFactory()
    client = Client()

    response = sign_in(client, user.email, "wrong-password")

    assert response.status_code == 200
    assert response.context["form"].errors
    assert "_auth_user_id" not in client.session
    assert SecurityEvent.objects.filter(type=SecurityEventType.LOGIN_FAILED).get().identifier == user.email


def test_does_not_let_deactivated_accounts_sign_in() -> None:
    user = UserFactory(inactive=True)
    client = Client()

    response = sign_in(client, user.email)

    assert response.status_code == 200
    assert response.context["form"].errors
    assert "_auth_user_id" not in client.session


def test_asks_enrolled_users_for_a_two_factor_code() -> None:
    user = UserFactory(with_mfa=True)
    client = Client()

    response = sign_in(client, user.email)

    assert response.status_code == 302
    assert response["Location"] == CHALLENGE
    assert "_auth_user_id" not in client.session

    response = client.post(CHALLENGE, {"code": current_otp()})

    assert response.status_code == 302
    assert response["Location"] == "/portal/"
    assert int(client.session["_auth_user_id"]) == user.pk


def test_remembers_a_device_after_a_successful_challenge_when_asked(
    set_security_settings: Callable[..., None],
) -> None:
    set_security_settings(mfa_remember_device_days=30)
    user = UserFactory(with_mfa=True)
    client = Client()

    sign_in(client, user.email)
    response = client.post(CHALLENGE, {"code": current_otp(), "remember_device": "1"})

    assert COOKIE in response.cookies
    client.post("/accounts/logout/")
    assert "_auth_user_id" not in client.session

    response = sign_in(client, user.email)

    assert response["Location"] == "/portal/"
    assert int(client.session["_auth_user_id"]) == user.pk


def test_does_not_trust_a_remembered_device_after_the_two_factor_enrollment_changes(
    set_security_settings: Callable[..., None],
) -> None:
    set_security_settings(mfa_remember_device_days=30)
    user = UserFactory(with_mfa=True)
    trusted = TrustedDevices()
    response = Client().get("/accounts/login/")
    trusted.remember(response, user)
    request = RequestFactory().get("/")
    request.COOKIES[COOKIE] = response.cookies[COOKIE].value

    assert trusted.is_trusted(request, user)

    user.email_mfa_enabled_at = timezone.now() + timedelta(minutes=1)
    user.save()

    assert not trusted.is_trusted(request, user)


def test_ignores_remembered_devices_when_the_policy_turns_the_feature_off(
    set_security_settings: Callable[..., None],
) -> None:
    set_security_settings(mfa_remember_device_days=30)
    user = UserFactory(with_mfa=True)
    response = Client().get("/accounts/login/")
    TrustedDevices().remember(response, user)
    client = Client()
    client.cookies[COOKIE] = response.cookies[COOKIE].value

    set_security_settings(mfa_remember_device_days=0)

    assert sign_in(client, user.email)["Location"] == CHALLENGE
