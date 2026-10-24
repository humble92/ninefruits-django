"""Original tests/Feature/Security/SignInMethodsTest.php: student number sign-in, the same
failure for every reason, the account lockout, and school sign-in (SSO) with a fake OIDC
provider (linking by institutional email, second factor after SSO)."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
import time_machine
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentRecord
from ninefruits.security import views_sso
from ninefruits.security.crypto import encrypt_string
from ninefruits.security.enums import MfaEnforcement, SsoLinkMode, StudentNumberLogin
from ninefruits.security.models import User, UserIdentity
from ninefruits.security.services.oidc import OidcClient
from tests.factories.person import StudentRecordFactory
from tests.factories.security import PASSWORD, UserFactory, current_otp
from tests.security.conftest import confirm_password, signed_in

pytestmark = pytest.mark.django_db

FAILED = "These credentials do not match our records."


def set_record_status(record_id: int, status: str) -> None:
    StudentRecord.objects.filter(pk=record_id).update(
        status=status, graduation_date=date(2026, 2, 20) if status == StudentStatus.GRADUATED else None
    )


@pytest.fixture
def student(set_security_settings: Callable[..., None]) -> tuple[User, int]:
    set_security_settings(mfa_enforcement=MfaEnforcement.RECOMMENDED)
    record = StudentRecordFactory(student_number="202612345")
    return UserFactory(person=record.person, email="minsu@example.test"), record.pk


def sign_in(client: Client, identifier: str, password: str = PASSWORD) -> Any:
    return client.post("/accounts/login/", {"login": identifier, "password": password})


def signed_in_as(client: Client) -> int | None:
    value = client.session.get("_auth_user_id")
    return int(value) if value else None


@pytest.mark.parametrize(
    ("setting", "status", "allowed"),
    [
        (StudentNumberLogin.DISABLED, "enrolled", False),
        (StudentNumberLogin.ACTIVE_RECORDS, "enrolled", True),
        (StudentNumberLogin.ACTIVE_RECORDS, "on_leave", True),
        (StudentNumberLogin.ACTIVE_RECORDS, "graduated", False),
        (StudentNumberLogin.ALL_RECORDS, "graduated", True),
    ],
    ids=[
        "disabled",
        "active records, enrolled",
        "active records, on leave",
        "active records, graduated",
        "all records, graduated",
    ],
)
def test_signs_in_with_a_student_number_according_to_the_setting(
    student: tuple[User, int],
    set_authentication_settings: Callable[..., None],
    setting: StudentNumberLogin,
    status: str,
    allowed: bool,
) -> None:
    user, record_id = student
    set_authentication_settings(student_number_login=setting)
    set_record_status(record_id, status)
    client = Client()

    sign_in(client, "202612345")

    assert signed_in_as(client) == (user.pk if allowed else None)


def test_always_accepts_the_personal_email_and_gives_the_same_error_for_every_failure(
    student: tuple[User, int], set_authentication_settings: Callable[..., None]
) -> None:
    user, _record = student
    set_authentication_settings(student_number_login=StudentNumberLogin.ACTIVE_RECORDS)
    client = Client()

    wrong_password = sign_in(client, "202612345", "wrong")
    unknown = sign_in(client, "999999999")

    assert wrong_password.context["form"].non_field_errors() == [FAILED]
    assert unknown.context["form"].non_field_errors() == [FAILED]

    sign_in(client, "minsu@example.test")
    assert signed_in_as(client) == user.pk


def test_locks_the_account_after_repeated_failures_counted_across_email_and_student_number(
    student: tuple[User, int], set_authentication_settings: Callable[..., None]
) -> None:
    user, _record = student
    set_authentication_settings(
        student_number_login=StudentNumberLogin.ACTIVE_RECORDS, lockout_threshold=4, lockout_minutes=15
    )

    for identifier in ["202612345", "minsu@example.test", "202612345", "minsu@example.test"]:
        sign_in(Client(), identifier, "wrong")

    user.refresh_from_db()
    assert user.is_locked()

    client = Client()
    response = sign_in(client, "minsu@example.test")
    assert signed_in_as(client) is None
    assert response.context["form"].non_field_errors() == [FAILED]

    with time_machine.travel(timezone.now() + timedelta(minutes=16)):
        sign_in(client, "minsu@example.test")
        assert signed_in_as(client) == user.pk
    user.refresh_from_db()
    assert user.locked_until is None


def test_lets_an_sso_linked_graduate_sign_in_with_the_personal_email(
    student: tuple[User, int], set_authentication_settings: Callable[..., None]
) -> None:
    user, record_id = student
    UserIdentity.objects.create(user=user, provider="school", subject="sub-123")
    set_record_status(record_id, "graduated")
    client = Client()

    sign_in(client, "minsu@example.test")
    assert signed_in_as(client) == user.pk

    client.post("/accounts/logout/")
    set_authentication_settings(password_login_for_sso_users=False)

    sign_in(client, "minsu@example.test")
    assert signed_in_as(client) is None


# -- SSO with a fake OIDC provider. Keys are generated per test run. ---------------------------
ISSUER = "https://idp.example.test"


class FakeProvider:
    def __init__(self) -> None:
        from cryptography.hazmat.primitives.asymmetric import rsa

        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.next_id_token = ""
        jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(self.private_key.public_key()))
        self.jwks = {"keys": [{**jwk, "alg": "RS256", "use": "sig", "kid": "test-key"}]}

    def handler(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == f"{ISSUER}/.well-known/openid-configuration":
            return httpx.Response(
                200,
                json={
                    "issuer": ISSUER,
                    "authorization_endpoint": f"{ISSUER}/authorize",
                    "token_endpoint": f"{ISSUER}/token",
                    "jwks_uri": f"{ISSUER}/jwks",
                },
            )
        if url == f"{ISSUER}/jwks":
            return httpx.Response(200, json=self.jwks)
        if url == f"{ISSUER}/token":
            return httpx.Response(200, json={"id_token": self.next_id_token})
        return httpx.Response(404)

    def sign(self, claims: dict[str, Any]) -> str:
        return jwt.encode(claims, self.private_key, algorithm="RS256", headers={"kid": "test-key"})


@pytest.fixture
def fake_provider(monkeypatch: pytest.MonkeyPatch, set_authentication_settings: Callable[..., None]) -> FakeProvider:
    provider = FakeProvider()
    transport = httpx.MockTransport(provider.handler)
    monkeypatch.setattr(views_sso, "oidc_client_factory", lambda: OidcClient(httpx.Client(transport=transport)))
    set_authentication_settings(
        sso_providers=[
            {
                "key": "school",
                "label": "School account",
                "issuer": ISSUER,
                "client_id": "sis-client",
                "client_secret": encrypt_string("secret"),
                "scopes": "openid email",
                "trusts_mfa": False,
                "is_enabled": True,
            }
        ]
    )
    return provider


def sso_sign_in(client: Client, provider: FakeProvider, claims: dict[str, Any]) -> Any:
    """Runs the browser part of the flow and returns the callback response."""
    redirect = client.get("/auth/sso/school/redirect/")
    assert redirect.status_code == 302
    query = parse_qs(urlparse(redirect["Location"]).query)
    assert query["code_challenge_method"] == ["S256"]
    now = int(time.time())
    provider.next_id_token = provider.sign(
        {"iss": ISSUER, "aud": "sis-client", "iat": now, "exp": now + 300, "nonce": query["nonce"][0], **claims}
    )
    return client.get("/auth/sso/school/callback/", {"state": query["state"][0], "code": "abc"})


def test_signs_in_with_a_linked_school_account(student: tuple[User, int], fake_provider: FakeProvider) -> None:
    user, _record = student
    UserIdentity.objects.create(user=user, provider="school", subject="sub-123")
    client = Client()

    response = sso_sign_in(client, fake_provider, {"sub": "sub-123"})

    assert response.status_code == 302
    assert response["Location"] == "/portal/"
    assert signed_in_as(client) == user.pk


@pytest.mark.parametrize(
    "claims",
    [{"aud": "another-client"}, {"nonce": "replayed"}, {"iss": "https://evil.example.test"}],
    ids=["audience", "nonce", "issuer"],
)
def test_rejects_tokens_with_a_wrong_audience_or_nonce(
    student: tuple[User, int], fake_provider: FakeProvider, claims: dict[str, Any]
) -> None:
    user, _record = student
    UserIdentity.objects.create(user=user, provider="school", subject="sub-123")
    client = Client()

    response = sso_sign_in(client, fake_provider, {"sub": "sub-123", **claims})

    assert response.status_code == 302
    assert response["Location"] == "/accounts/login/"
    assert signed_in_as(client) is None


def test_links_on_first_sign_in_by_institutional_email_when_configured_otherwise_asks_to_link_manually(
    student: tuple[User, int], fake_provider: FakeProvider, set_authentication_settings: Callable[..., None]
) -> None:
    user, record_id = student
    StudentRecord.objects.filter(pk=record_id).update(institutional_email="minsu@school.example.test")
    claims = {"sub": "sub-new", "email": "minsu@school.example.test", "email_verified": True}
    client = Client()

    response = sso_sign_in(client, fake_provider, claims)
    assert response["Location"] == "/accounts/login/"
    assert signed_in_as(client) is None

    set_authentication_settings(sso_link_mode=SsoLinkMode.INSTITUTIONAL_EMAIL)

    response = sso_sign_in(client, fake_provider, claims)
    assert response["Location"] == "/portal/"
    assert signed_in_as(client) == user.pk
    assert UserIdentity.objects.get(subject="sub-new").user_id == user.pk


def test_still_asks_enrolled_users_for_their_second_factor_after_sso(
    student: tuple[User, int], fake_provider: FakeProvider
) -> None:
    user = UserFactory(with_mfa=True)
    UserIdentity.objects.create(user=user, provider="school", subject="sub-mfa")
    client = Client()

    response = sso_sign_in(client, fake_provider, {"sub": "sub-mfa"})
    assert response["Location"] == reverse("security:two_factor_challenge")
    assert signed_in_as(client) is None

    response = client.post(reverse("security:two_factor_challenge"), {"code": current_otp()})
    assert response.status_code == 302
    assert response["Location"] == "/portal/"
    assert signed_in_as(client) == user.pk


def test_links_a_school_account_from_the_security_page_after_password_confirmation(
    student: tuple[User, int], fake_provider: FakeProvider
) -> None:
    user, _record = student
    client = signed_in(user)

    response = client.get("/auth/sso/school/redirect/?link=1")
    assert response["Location"].startswith(reverse("account_reauthenticate"))

    confirm_password(client)
    response = sso_sign_in_link(client, fake_provider, {"sub": "sub-777", "email": "kim@school.example.test"})
    assert response["Location"] == reverse("portal:security")
    identity = UserIdentity.objects.get(subject="sub-777")
    assert identity.user_id == user.pk
    assert identity.email == "kim@school.example.test"


def sso_sign_in_link(client: Client, provider: FakeProvider, claims: dict[str, Any]) -> Any:
    redirect = client.get("/auth/sso/school/redirect/?link=1")
    query = parse_qs(urlparse(redirect["Location"]).query)
    now = int(time.time())
    provider.next_id_token = provider.sign(
        {"iss": ISSUER, "aud": "sis-client", "iat": now, "exp": now + 300, "nonce": query["nonce"][0], **claims}
    )
    return client.get("/auth/sso/school/callback/", {"state": query["state"][0], "code": "abc"})
