"""Original tests/Feature/Security/SecurityCommandsTest.php (security commands; the
people_find_duplicates case comes with the person app in Phase 2) plus the
security_create_administrator and security_sync_permissions commands."""

from __future__ import annotations

import io
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from ninefruits.audit.models import ActivityLog, SecurityEvent
from ninefruits.security.enums import Permission
from ninefruits.security.models import Permission as PermissionModel
from ninefruits.security.models import Role
from ninefruits.security.role_templates import sync_role_templates
from tests.factories.security import RoleFactory, UserFactory, has_authenticator_app

pytestmark = pytest.mark.django_db


def run(name: str, *args: str, stdin: str | None = None, monkeypatch: pytest.MonkeyPatch | None = None) -> int:
    if stdin is not None and monkeypatch is not None:
        monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    return int(call_command(name, *args, stdout=io.StringIO(), stderr=io.StringIO()))


def test_resets_two_factor_authentication_only_with_a_reason_and_an_actor() -> None:
    admin = UserFactory(email="lead@example.test")
    user = UserFactory(email="lost-phone@example.test", with_mfa=True)

    assert run("security_reset_mfa", user.email) == 1
    assert run("security_reset_mfa", user.email, "--reason", "Lost phone") == 1
    assert has_authenticator_app(user)

    assert run("security_reset_mfa", user.email, "--reason", "Lost phone", "--actor", admin.email) == 0

    assert not has_authenticator_app(user)
    assert ActivityLog.objects.get(event="mfa.reset").reason == "Lost phone"


def test_unlocks_a_locked_account() -> None:
    user = UserFactory(
        email="locked@example.test", locked_until=timezone.now() + timedelta(hours=1), failed_login_count=3
    )

    assert run("security_unlock_user", user.email) == 1
    assert run("security_unlock_user", user.email, "--reason", "Called the help desk") == 0

    user.refresh_from_db()
    assert not user.is_locked()
    assert user.failed_login_count == 0
    assert SecurityEvent.objects.filter(type="account.unlocked").exists()


def test_creates_an_administrator_with_the_password_from_standard_input(monkeypatch: pytest.MonkeyPatch) -> None:
    sync_role_templates()

    status = run(
        "security_create_administrator",
        "--email",
        "Admin@Example.test",
        "--name",
        "First Admin",
        "--password-stdin",
        stdin="Correct-Horse-Battery-9\n",
        monkeypatch=monkeypatch,
    )

    assert status == 0
    user = UserFactory._meta.model.objects.get(email="admin@example.test")
    assert user.check_password("Correct-Horse-Battery-9")
    assert user.email_verified_at is not None
    assert user.has_perm(Permission.ADMIN_PANEL_ACCESS)
    assert user.role_assignments.get().role.name == "system_administrator"
    assert ActivityLog.objects.filter(event="command.executed", log_name="command").exists()


def test_refuses_to_create_an_administrator_without_the_role_or_with_a_weak_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = ("--email", "admin@example.test", "--name", "Admin", "--password-stdin")
    assert run("security_create_administrator", *args, stdin="Correct-Horse-Battery-9\n", monkeypatch=monkeypatch) == 1

    sync_role_templates()
    assert run("security_create_administrator", *args, stdin="short\n", monkeypatch=monkeypatch) == 1
    assert not UserFactory._meta.model.objects.filter(email="admin@example.test").exists()


def test_synchronizes_the_permission_catalog() -> None:
    PermissionModel.objects.all().delete()
    PermissionModel.objects.create(name="obsolete.permission")
    system = RoleFactory(is_system=True)

    assert run("security_sync_permissions", "--dry-run") == 0
    assert PermissionModel.objects.filter(name="obsolete.permission").exists()
    assert PermissionModel.objects.count() == 1

    # Deleting needs --force (or a confirmation at a terminal).
    assert run("security_sync_permissions") == 1
    assert run("security_sync_permissions", "--force") == 0

    assert sorted(PermissionModel.objects.values_list("name", flat=True)) == sorted(p.value for p in Permission)
    assert len(system.permission_names()) == len(Permission)


def test_role_templates_are_idempotent_and_keep_administrator_changes() -> None:
    created = sync_role_templates()
    assert "registrar" in created and "student" in created

    registrar = Role.objects.get(name="registrar")
    registrar.sync_permissions([Permission.USERS_VIEW.value])
    registrar.display_name = {"en": "Records office"}
    registrar.save()
    student = Role.objects.get(name="student")
    student.persona = None
    student.save()

    assert sync_role_templates() == []

    registrar.refresh_from_db()
    assert registrar.permission_names() == [Permission.USERS_VIEW.value]
    assert str(registrar.display_name) == "Records office"
    assert Role.objects.get(name="student").persona == "student"
    assert len(Role.objects.get(name="system_administrator").permission_names()) == len(Permission)
