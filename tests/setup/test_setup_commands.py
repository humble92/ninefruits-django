"""Original tests/Feature/Setup/SetupCommandsTest.php (Phase 1 parts; the administrator cases
are in tests/security/test_security_commands.py)."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command
from django.test import override_settings

from ninefruits.security.actions import AssignRole
from ninefruits.security.enums import Permission
from ninefruits.security.models import Role, User
from ninefruits.settings.groups.institution import InstitutionSettings
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.essential import EssentialSeeder
from ninefruits.setup.seeders.profiles.korean_university import seed_scale_45
from tests.factories.security import UserFactory

# setup_install runs migrate on the schema owner connection (nothing to apply in tests).
pytestmark = [pytest.mark.django_db(databases=["default", "migrator"]), pytest.mark.usefixtures("essential_data")]


@pytest.fixture
def administrator(essential_data: None) -> User:
    admin = UserFactory()
    AssignRole()(admin, Role.objects.get(name="system_administrator"), "test")
    return admin


@pytest.mark.usefixtures("administrator")
def test_installs_essential_data_and_institution_settings_without_questions() -> None:
    assert (
        call_command(
            "setup_install",
            force=True,
            locale="ko",
            timezone="Asia/Seoul",
            institution_name="데모 대학교",
            stdout=StringIO(),
        )
        == 0
    )

    InstitutionSettings.invalidate()
    settings = InstitutionSettings.load()
    assert settings.default_locale == "ko"
    assert settings.timezone == "Asia/Seoul"
    assert settings.name["ko"] == "데모 대학교"
    assert Role.objects.filter(name="registrar").exists()


@pytest.mark.usefixtures("administrator")
def test_refuses_an_unknown_time_zone_without_changing_the_settings() -> None:
    before = InstitutionSettings.load().timezone
    err = StringIO()

    call_command("setup_install", force=True, timezone="Mars/Olympus", stdout=StringIO(), stderr=err)

    InstitutionSettings.invalidate()
    assert InstitutionSettings.load().timezone == before
    assert "Unsupported language or time zone" in err.getvalue()


@pytest.mark.usefixtures("administrator")
def test_fixes_the_grade_scale_once() -> None:
    assert call_command("setup_install", force=True, grade_scale="4.3", stdout=StringIO()) == 0
    err = StringIO()

    assert call_command("setup_install", force=True, grade_scale="4.5", stdout=StringIO(), stderr=err) == 1
    assert "cannot change" in err.getvalue()


@pytest.mark.usefixtures("administrator")
def test_keeps_the_scale_fixed_by_an_earlier_profile() -> None:
    seed_scale_45(True)

    assert call_command("setup_install", force=True, grade_scale="4.5", stdout=StringIO()) == 0


def test_keeps_values_administrators_changed_when_essential_seeders_run_again() -> None:
    registrar = Role.objects.get(name="registrar")
    registrar.display_name = {"en": "Student Records Office"}
    registrar.save()
    registrar.sync_permissions([])

    EssentialSeeder()()

    registrar.refresh_from_db()
    assert Role.objects.filter(name="registrar").count() == 1
    assert registrar.display_name_translations == {"en": "Student Records Office"}
    assert registrar.permissions.count() == 0
    assert Role.objects.get(name="system_administrator").permissions.count() == len(Permission)


def test_creates_demo_accounts_and_can_run_twice() -> None:
    out = StringIO()
    assert call_command("setup_demo", force=True, size="tiny", stdout=out) == 0
    assert call_command("setup_demo", force=True, size="tiny", stdout=StringIO()) == 0

    for email in DemoAccountSeeder.emails():
        assert User.objects.filter(email=email).count() == 1
        assert email in out.getvalue()
    assert User.objects.get(email="registrar@demo.test").has_perm(Permission.ADMIN_PANEL_ACCESS)


@override_settings(DJANGO_ENV="production")
def test_never_creates_demo_data_in_production() -> None:
    assert call_command("setup_demo", force=True, stdout=StringIO(), stderr=StringIO()) == 1

    assert not User.objects.filter(email__endswith="@demo.test").exists()


def test_refuses_an_unknown_demo_size() -> None:
    assert call_command("setup_demo", force=True, size="huge", stdout=StringIO(), stderr=StringIO()) == 1


def test_writes_the_load_test_accounts_file() -> None:
    from django.core.files.storage import default_storage

    assert call_command("setup_demo", force=True, size="tiny", student_accounts=True, stdout=StringIO()) == 0

    with default_storage.open("load-accounts.csv") as handle:
        assert handle.read().decode().splitlines()[0] == "email,password"


def test_creates_the_first_administrator_interactively(monkeypatch: pytest.MonkeyPatch) -> None:
    import getpass
    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(getpass, "getpass", lambda prompt="": "Correct-Horse-Battery-9")

    status = call_command(
        "security_create_administrator", email="first@example.com", name="First Admin", stdout=StringIO()
    )

    assert status == 0
    assert User.objects.get(email="first@example.com").has_perm(Permission.SECURITY_SETTINGS_MANAGE)


def test_refuses_a_non_interactive_administrator_without_password_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    status = call_command(
        "security_create_administrator", email="x@example.com", name="X", stdout=StringIO(), stderr=StringIO()
    )

    assert status == 1
    assert not User.objects.filter(email="x@example.com").exists()


@pytest.mark.usefixtures("administrator")
def test_skips_the_administrator_when_one_exists() -> None:
    out = StringIO()

    assert call_command("setup_install", force=True, stdout=out) == 0
    assert "exists" in out.getvalue()
