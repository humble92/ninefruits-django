"""Portal layout and dashboard (original app/Livewire/Portal/Dashboard.php,
components/layouts/portal, x-mfa-reminder, x-locale-switcher; tests/Feature/Person/PortalTest.php
and tests/Feature/Admin/AdminPagesTest.php cases that only need the layout). Persona pages are
ported with their phases."""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from django.contrib.messages import constants
from django.template import Context, Template
from django.test import Client, RequestFactory
from django.urls import resolve
from django.utils import translation

from ninefruits.portal import menu
from ninefruits.portal.templatetags.portal import reminder_message
from ninefruits.security.actions.assign_role import AssignRole
from ninefruits.security.enums import MfaEnforcement, Permission, Persona
from ninefruits.security.models import Role, User
from ninefruits.settings.groups.security import SecuritySettings

pytestmark = pytest.mark.django_db


def set_mfa(enforcement: MfaEnforcement) -> None:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = enforcement
    settings.save()


@pytest.fixture(autouse=True)
def _mfa_disabled() -> Iterator[None]:
    set_mfa(MfaEnforcement.DISABLED)
    yield
    SecuritySettings.invalidate()


def make_user(*permissions: str, name: str = "Kim Minjun", **fields: Any) -> User:
    user = User.objects.create_user(
        email=f"{uuid.uuid4().hex[:12]}@example.test", password="secret-password", name=name, **fields
    )
    if permissions:
        role = Role.objects.create(name=f"role_{uuid.uuid4().hex[:8]}", display_name={"en": "Registrar office"})
        role.sync_permissions([str(permission) for permission in permissions])
        AssignRole()(user, role, "Test setup")
    return user


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def test_guests_are_sent_to_sign_in() -> None:
    response = Client().get("/portal/")

    assert response.status_code == 302
    assert response["Location"] == "/accounts/login/?next=/portal/"


def test_root_redirects_to_the_portal() -> None:
    response = signed_in(make_user()).get("/")

    assert response.status_code == 302
    assert response["Location"] == "/portal/"


def test_dashboard_welcomes_the_user_and_shows_access() -> None:
    response = signed_in(make_user(name="Kim Minjun")).get("/portal/")

    content = response.content.decode()
    assert response.status_code == 200
    assert "Welcome, Kim Minjun" in content
    assert "Your access" in content
    assert re.search(r"data-roles>\s*None", content)
    assert re.search(r"data-personas>\s*None", content)


def test_dashboard_lists_active_roles() -> None:
    response = signed_in(make_user(Permission.USERS_VIEW)).get("/portal/")

    assert response.status_code == 200
    assert "data-roles>None" not in response.content.decode()


def test_admin_link_only_with_panel_access() -> None:
    without = signed_in(make_user()).get("/portal/").content.decode()
    with_access = signed_in(make_user(Permission.ADMIN_PANEL_ACCESS)).get("/portal/").content.decode()

    assert 'href="/admin/"' not in without
    assert 'href="/admin/"' in with_access
    assert "Administration" in with_access


def test_layout_has_navigation_locale_switcher_and_sign_out() -> None:
    content = signed_in(make_user()).get("/portal/").content.decode()

    assert 'href="/portal/"' in content
    assert 'action="/i18n/locale/"' in content
    assert 'name="locale"' in content
    assert 'action="/accounts/logout/"' in content


def test_htmx_requests_carry_the_csrf_token() -> None:
    content = signed_in(make_user()).get("/portal/").content.decode()

    assert re.search(r"hx-headers='\{\"X-CSRFToken\": \"[^\"]+\"\}'", content)


def test_scripts_carry_the_csp_nonce() -> None:
    response = signed_in(make_user()).get("/portal/")
    nonce = re.search(r"'nonce-([^']+)'", response["Content-Security-Policy"])

    assert nonce is not None
    scripts = re.findall(r"<script[^>]*>", response.content.decode())
    assert scripts
    assert all(f'nonce="{nonce.group(1)}"' in script for script in scripts)


def test_flash_messages_are_shown() -> None:
    from django.contrib.messages.storage.fallback import FallbackStorage

    request = RequestFactory().get("/portal/")
    request.session = {}  # type: ignore[assignment]
    storage = FallbackStorage(request)
    storage.add(constants.SUCCESS, "Saved")
    html = Template('{% include "partials/messages.html" %}').render(Context({"messages": storage}))

    assert 'role="status"' in html
    assert "Saved" in html


def test_renders_in_korean() -> None:
    response = signed_in(make_user(locale="ko")).get("/portal/")

    content = response.content.decode()
    assert '<html lang="ko">' in content
    assert "홈" in content
    assert "로그아웃" in content


# -- navigation registry ------------------------------------------------------------------------


@pytest.fixture
def student_item() -> Iterator[None]:
    menu.register("records", "My records", "portal:dashboard", order=20, personas={Persona.STUDENT, Persona.ALUMNI})
    yield
    menu.unregister("records")


def _request(user: User) -> Any:
    request = RequestFactory().get("/portal/")
    request.user = user
    request.resolver_match = resolve("/portal/")
    return request


def test_menu_hides_persona_pages_from_other_users(student_item: None) -> None:
    keys = [item["key"] for item in menu.items_for(_request(make_user()))]

    assert "records" not in keys
    assert keys[0] == "dashboard"


def test_menu_shows_persona_pages_to_the_persona(student_item: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(menu, "persona_values", lambda request: {"student"})

    items = menu.items_for(_request(make_user()))

    assert [item["key"] for item in items][:2] == ["dashboard", "records"]
    assert items[0]["active"] is True


def test_menu_items_with_unresolvable_urls_are_skipped() -> None:
    menu.register("later", "Later", "portal:does-not-exist")
    try:
        assert "later" not in [item["key"] for item in menu.items_for(_request(make_user()))]
    finally:
        menu.unregister("later")


def test_menu_permission_items() -> None:
    menu.register("reports", "Reports", "portal:dashboard", permission=Permission.REPORTS_VIEW)
    try:
        assert "reports" not in [item["key"] for item in menu.items_for(_request(make_user()))]
        allowed = make_user(Permission.REPORTS_VIEW)
        assert "reports" in [item["key"] for item in menu.items_for(_request(allowed))]
    finally:
        menu.unregister("reports")


# -- two-factor reminder ------------------------------------------------------------------------


def test_recommended_policy_shows_the_reminder() -> None:
    set_mfa(MfaEnforcement.RECOMMENDED)

    content = signed_in(make_user()).get("/portal/").content.decode()

    assert "data-mfa-reminder" in content
    assert "We recommend enabling two-factor authentication" in content


def test_no_reminder_when_two_factor_is_disabled() -> None:
    assert "data-mfa-reminder" not in signed_in(make_user()).get("/portal/").content.decode()


def test_required_reminder_shows_the_deadline() -> None:
    with translation.override("en"):
        message = reminder_message({"required": True, "deadline": datetime(2026, 11, 3, 12, tzinfo=UTC)})

    assert message is not None
    assert "required" in message
    assert "2026" in message


def test_reminder_is_not_shown_on_the_security_page() -> None:
    request = RequestFactory().get("/portal/security/")
    request.mfa_reminder = {"required": False, "deadline": None}  # type: ignore[attr-defined]
    request.resolver_match = type("Match", (), {"view_name": "portal:security"})()  # type: ignore[assignment]

    html = Template("{% load portal %}{% mfa_reminder %}").render(Context({"request": request}))

    assert "data-mfa-reminder" not in html


def test_admin_pages_show_the_reminder() -> None:
    set_mfa(MfaEnforcement.RECOMMENDED)
    user = make_user(*Permission)

    content = signed_in(user).get("/admin/").content.decode()

    assert "data-mfa-reminder" in content


def test_messages_from_the_locale_switch_are_shown() -> None:
    client = signed_in(make_user())

    response = client.post("/i18n/locale/", {"locale": "xx", "next": "/portal/"}, follow=True)

    assert response.status_code == 200
    assert 'role="alert"' in response.content.decode()
