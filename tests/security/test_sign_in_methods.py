"""Original tests/Feature/Security/SignInMethodsTest.php: student number sign-in, the same
failure for every reason, and the account lockout. The SSO cases (fake OIDC provider, linking
by institutional email, second factor after SSO) are Phase 2 with the SSO sign-in flow."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
import time_machine
from django.db import connection
from django.test import Client
from django.utils import timezone

from ninefruits.security.enums import MfaEnforcement, StudentNumberLogin
from ninefruits.security.models import User, UserIdentity
from tests.factories.security import PASSWORD, UserFactory
from tests.security.conftest import create_program

pytestmark = pytest.mark.django_db

FAILED = "These credentials do not match our records."


def create_student_record(student_number: str) -> tuple[int, int]:
    """A person with a student record (person models arrive in Phase 2). Returns
    (person_id, student_record_id)."""
    program_id = create_program()
    with connection.cursor() as cursor:
        cursor.execute("SELECT org_unit_id FROM programs WHERE id = %s", [program_id])
        org_unit_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO people (family_name, given_name, created_at, updated_at) VALUES (%s, %s, now(), now()) "
            "RETURNING id",
            ["Kim", "Minsu"],
        )
        person_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO student_records (person_id, student_number, program_id, org_unit_id, admission_date, "
            "catalog_year, created_at, updated_at) VALUES (%s, %s, %s, %s, '2026-03-02', 2026, now(), now()) "
            "RETURNING id",
            [person_id, student_number, program_id, org_unit_id],
        )
        return person_id, cursor.fetchone()[0]


def set_record_status(record_id: int, status: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE student_records SET status = %s, graduation_date = CASE WHEN %s = 'graduated' "
            "THEN DATE '2026-02-20' END WHERE id = %s",
            [status, status, record_id],
        )


@pytest.fixture
def student(set_security_settings: Callable[..., None]) -> tuple[User, int]:
    set_security_settings(mfa_enforcement=MfaEnforcement.RECOMMENDED)
    person_id, record_id = create_student_record("202612345")
    return UserFactory(person_id=person_id, email="minsu@example.test"), record_id


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
