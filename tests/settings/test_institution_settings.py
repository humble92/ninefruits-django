"""Institution settings: settings migrations (original database/settings/*institution*, *lao*),
the settings group and the admin page (original ManageInstitutionSettings + SettingsPage)."""

from __future__ import annotations

import importlib
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from django.apps import apps as global_apps
from django.conf import settings as django_settings
from django.contrib import admin
from django.test import Client
from django.urls import reverse

from ninefruits.security.actions.assign_role import AssignRole
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.security.models import Role, User
from ninefruits.settings.admin_views import (
    SettingsPage,
    get_settings_urls,
    pages_for,
    register_settings_page,
    settings_pages,
    sidebar_items,
)
from ninefruits.settings.groups.institution import InstitutionSettings
from ninefruits.settings.groups.security import SecuritySettings
from ninefruits.settings.models import SettingValue
from ninefruits.settings.pages.institution import ManageInstitutionSettings

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mfa_disabled() -> Iterator[None]:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()
    yield
    SecuritySettings.invalidate()


@pytest.fixture
def audits(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    recorded: list[dict[str, Any]] = []

    def record(event: str, subject: Any = None, **kwargs: Any) -> None:
        recorded.append({"event": event, "subject": subject, **kwargs})

    monkeypatch.setattr("ninefruits.audit.logger.audit", record)
    return recorded


def make_user(*permissions: str) -> User:
    user = User.objects.create_user(email=f"{uuid.uuid4().hex[:12]}@example.test", password="secret-password")
    if permissions:
        role = Role.objects.create(name=f"role_{uuid.uuid4().hex[:8]}", guard_name="web", display_name={"en": "Test"})
        role.sync_permissions([str(permission) for permission in permissions])
        AssignRole()(user, role, "Test setup")
    return user


def signed_in(*permissions: str) -> Client:
    client = Client()
    client.force_login(make_user(*permissions))
    return client


PAGE = "/admin/settings/institution/"


# -- settings migrations ---------------------------------------------------------------------------
def test_migrations_create_the_institution_settings_with_lao() -> None:
    rows = {row.name: row.payload for row in SettingValue.objects.filter(group="institution")}
    assert rows["supported_locales"] == ["en", "ko", "zh-hans", "lo"]
    assert rows["default_locale"] == "en"
    assert rows["name"] == {"en": django_settings.APP_NAME}
    assert rows["timezone"]
    loaded = InstitutionSettings.load()
    assert loaded.supported_locales == ["en", "ko", "zh-hans", "lo"]


class _Apps:
    def get_model(self, app_label: str, model: str) -> type[SettingValue]:
        return global_apps.get_model(app_label, model)


def test_lao_migration_only_extends_the_shipped_default() -> None:
    lao = importlib.import_module("ninefruits.settings.migrations.0006_lao_locale")
    row = SettingValue.objects.get(group="institution", name="supported_locales")

    row.payload = ["zh-hans", "en", "ko"]
    row.save()
    lao.forwards(_Apps(), None)
    row.refresh_from_db()
    assert row.payload == ["zh-hans", "en", "ko", "lo"]

    lao.backwards(_Apps(), None)
    row.refresh_from_db()
    assert row.payload == ["zh-hans", "en", "ko"]

    row.payload = ["en", "ko"]  # removed on purpose: kept
    row.save()
    lao.forwards(_Apps(), None)
    row.refresh_from_db()
    assert row.payload == ["en", "ko"]


def test_rejects_unknown_time_zones() -> None:
    settings = InstitutionSettings.load()
    with pytest.raises(ValueError, match="time zone"):
        settings.timezone = "Mars/Olympus"


# -- admin page --------------------------------------------------------------------------------
def test_institution_page_is_registered_and_mounted() -> None:
    assert ManageInstitutionSettings in settings_pages()
    names = {pattern.name for pattern in get_settings_urls(admin.site)}
    assert {"settings_index", "settings_institution"} <= names
    assert reverse("admin:settings_institution") == PAGE


def test_requires_the_permission() -> None:
    assert signed_in(Permission.ADMIN_PANEL_ACCESS).get(PAGE).status_code == 403
    assert signed_in(Permission.ADMIN_PANEL_ACCESS).get("/admin/settings/").status_code == 403
    assert Client().get(PAGE).status_code == 302  # to the sign-in page


def test_shows_the_form_filled_from_the_settings() -> None:
    settings = InstitutionSettings.load()
    settings.name = {"en": "Ninefruits University", "ko": "나인프루츠 대학교"}
    settings.save()
    client = signed_in(Permission.ADMIN_PANEL_ACCESS, Permission.INSTITUTION_SETTINGS_MANAGE)

    response = client.get(PAGE)

    assert response.status_code == 200
    html = response.content.decode()
    assert 'name="name__ko"' in html and "나인프루츠 대학교" in html
    assert 'value="lo"' in html and "ລາວ" in html
    assert "Asia/Seoul" in html
    assert "Offered languages" in html


def test_shows_the_page_in_korean() -> None:
    user = make_user(Permission.ADMIN_PANEL_ACCESS, Permission.INSTITUTION_SETTINGS_MANAGE)
    user.locale = "ko"
    user.save()
    client = Client()
    client.force_login(user)
    html = client.get(PAGE).content.decode()
    assert "기관 이름" in html and "제공 언어" in html


def test_saves_the_settings_and_records_the_audit(audits: list[dict[str, Any]]) -> None:
    client = signed_in(Permission.ADMIN_PANEL_ACCESS, Permission.INSTITUTION_SETTINGS_MANAGE)
    before = InstitutionSettings.load().model_dump(mode="json")

    response = client.post(
        PAGE,
        {
            "name__en": "Ninefruits University",
            "name__ko": "나인프루츠 대학교",
            "name__lo": "",
            "timezone": "Asia/Seoul",
            "supported_locales": ["en", "ko", "lo"],
            "default_locale": "zh-hans",  # not offered: the fallback language
        },
    )

    assert response.status_code == 302
    saved = InstitutionSettings.load()
    assert saved.name == {"en": "Ninefruits University", "ko": "나인프루츠 대학교"}
    assert saved.supported_locales == ["en", "ko", "lo"]
    assert saved.default_locale == "en"
    assert saved.timezone == "Asia/Seoul"
    assert audits == [
        {
            "event": "settings.updated",
            "subject": None,
            "properties": {"group": "institution", "before": before, "after": saved.model_dump(mode="json")},
            "log": "security",
        }
    ]


def test_writes_a_real_audit_entry() -> None:
    from ninefruits.audit.models import ActivityLog

    client = signed_in(Permission.ADMIN_PANEL_ACCESS, Permission.INSTITUTION_SETTINGS_MANAGE)
    client.post(
        PAGE,
        {"name__en": "N", "timezone": "UTC", "supported_locales": ["en", "ko"], "default_locale": "ko"},
    )
    entry = ActivityLog.objects.filter(event="settings.updated").order_by("-id").first()
    assert entry is not None and entry.log_name == "security"
    assert entry.properties["group"] == "institution"
    assert entry.properties["after"]["default_locale"] == "ko"


def test_validation_errors_keep_the_settings(audits: list[dict[str, Any]]) -> None:
    client = signed_in(Permission.ADMIN_PANEL_ACCESS, Permission.INSTITUTION_SETTINGS_MANAGE)
    before = InstitutionSettings.load()

    response = client.post(PAGE, {"name__ko": "이름만", "timezone": "Nowhere", "default_locale": "en"})

    assert response.status_code == 422
    errors = response.context["form"].errors
    assert set(errors) == {"name", "timezone", "supported_locales"}
    assert InstitutionSettings.load() == before
    assert audits == []


def test_settings_index_lists_the_groups_the_user_may_manage() -> None:
    client = signed_in(Permission.ADMIN_PANEL_ACCESS, Permission.INSTITUTION_SETTINGS_MANAGE)
    response = client.get("/admin/settings/")
    assert response.status_code == 200
    pages = [page for page, _url in response.context["settings_pages"]]
    assert ManageInstitutionSettings in pages
    assert all(page.permission in (Permission.INSTITUTION_SETTINGS_MANAGE,) for page in pages)


def test_sidebar_items_check_the_permission() -> None:
    from django.test import RequestFactory

    request = RequestFactory().get("/")
    request.user = make_user(Permission.ADMIN_PANEL_ACCESS)
    item = next(i for i in sidebar_items() if str(i["link"]) == PAGE)
    assert item["permission"](request) is False
    request.user = make_user(Permission.INSTITUTION_SETTINGS_MANAGE)
    assert item["permission"](request) is True
    assert ManageInstitutionSettings in pages_for(request)


def test_registering_a_page_requires_its_attributes() -> None:
    class Incomplete(SettingsPage):
        slug = "incomplete"

    with pytest.raises(TypeError, match="settings_class"):
        register_settings_page(Incomplete)


def test_admin_shell_strings_are_translated_in_lao() -> None:
    """unfold and Django ship no Lao: the overrides in locale/lo cover the admin shell."""
    user = make_user(Permission.ADMIN_PANEL_ACCESS, Permission.INSTITUTION_SETTINGS_MANAGE)
    user.locale = "lo"
    user.save()
    client = Client()
    client.force_login(user)
    html = client.get(PAGE).content.decode()
    assert "ອອກຈາກລະບົບ" in html  # Log out
    assert "ບັນທຶກ" in html  # Save
    assert "ພາສາທີ່ໃຫ້ເລືອກ" in html  # Offered languages
