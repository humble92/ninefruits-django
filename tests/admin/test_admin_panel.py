"""Admin panel frame (original tests/Feature/Admin/AdminPanelTest.php framework parts and
tests/Feature/Admin/AdminPagesTest.php dashboard/portal/locale cases).

Resource specific cases (users, roles, assignments, settings pages, audit screens) are ported
with the resources (tests/security, tests/settings, tests/audit)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.test import Client, RequestFactory
from django.urls import include, path, reverse

from ninefruits.adminpanel import navigation
from ninefruits.adminpanel.mixins import CatalogAdmin, ReadOnlyCatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup, build_navigation, register_link, unregister_link
from ninefruits.adminpanel.sites import NinefruitsAdminSite
from ninefruits.security.actions.assign_role import AssignRole
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.security.models import Role, User
from ninefruits.settings.groups.security import SecuritySettings

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mfa_disabled() -> Iterator[None]:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()
    yield
    SecuritySettings.invalidate()


def make_user(*permissions: str, **fields: Any) -> User:
    user = User.objects.create_user(
        email=f"{uuid.uuid4().hex[:12]}@example.test", password="secret-password", name="Staff Member", **fields
    )
    if permissions:
        role = Role.objects.create(name=f"role_{uuid.uuid4().hex[:8]}", display_name={"en": "Test role"})
        role.sync_permissions([str(permission) for permission in permissions])
        AssignRole()(user, role, "Test setup")
    return user


def administrator() -> User:
    return make_user(*Permission)


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


# -- access --------------------------------------------------------------------------------------


def test_admin_site_is_the_ninefruits_site() -> None:
    assert isinstance(admin.site, NinefruitsAdminSite)


def test_guests_are_sent_to_the_shared_sign_in() -> None:
    response = Client().get("/admin/")

    assert response.status_code == 302
    assert response["Location"].startswith("/accounts/login/")
    assert "next=" in response["Location"]


def test_there_is_no_admin_login_form() -> None:
    response = Client().get("/admin/login/?next=/admin/")

    assert response.status_code == 302
    assert response["Location"] == "/accounts/login/?next=/admin/"


def test_signed_in_staff_on_the_login_url_go_to_the_panel() -> None:
    response = signed_in(administrator()).get("/admin/login/")

    assert response.status_code == 302
    assert response["Location"] == "/admin/"


def test_renders_the_dashboard_for_staff_with_panel_access() -> None:
    user = administrator()
    response = signed_in(user).get("/admin/")

    assert response.status_code == 200
    content = response.content.decode()
    assert "data-account-widget" in content
    assert user.email in content


def test_users_without_admin_panel_access_get_403() -> None:
    assert signed_in(make_user()).get("/admin/").status_code == 403
    assert signed_in(make_user(Permission.USERS_VIEW)).get("/admin/").status_code == 403


def test_panel_access_alone_opens_the_dashboard() -> None:
    assert signed_in(make_user(Permission.ADMIN_PANEL_ACCESS)).get("/admin/").status_code == 200


def test_ending_the_assignment_closes_the_panel() -> None:
    user = make_user(Permission.ADMIN_PANEL_ACCESS)
    client = signed_in(user)
    assert client.get("/admin/").status_code == 200

    user.role_assignments.update(ends_at="2000-01-01T00:00:00Z")  # type: ignore[attr-defined]

    assert client.get("/admin/").status_code == 403


def test_inactive_users_cannot_open_the_panel() -> None:
    user = administrator()
    client = signed_in(user)
    User.objects.filter(pk=user.pk).update(is_active=False)

    response = client.get("/admin/")

    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


def test_logout_goes_through_allauth() -> None:
    client = signed_in(administrator())

    response = client.post("/admin/logout/")

    assert response.status_code == 302
    assert "_auth_user_id" not in client.session


def test_admin_responses_allow_unfold_scripts_under_csp() -> None:
    response = signed_in(administrator()).get("/admin/")

    policy = response["Content-Security-Policy"]
    assert "'unsafe-eval'" in policy
    assert "frame-ancestors 'none'" in policy


def test_portal_responses_keep_the_strict_policy() -> None:
    response = signed_in(administrator()).get("/portal/")

    assert "'unsafe-eval'" not in response["Content-Security-Policy"]
    assert "'nonce-" in response["Content-Security-Policy"]


def test_django_groups_are_not_in_the_admin() -> None:
    from django.contrib.auth.models import Group

    assert not admin.site.is_registered(Group)


# -- sidebar -------------------------------------------------------------------------------------


def _request(user: User, path_: str = "/admin/") -> HttpRequest:
    request = RequestFactory().get(path_)
    request.user = user
    return request


def _titles(nav: list[dict[str, Any]]) -> list[str]:
    return [group["title"] for group in nav]


def _items(nav: list[dict[str, Any]]) -> list[str]:
    return [item["title"] for group in nav for item in group["items"]]


@pytest.fixture
def report_link() -> Iterator[None]:
    register_link(
        group=NavigationGroup.REPORTS,
        label="Test reports",
        url_name="admin:index",
        permission=Permission.REPORTS_VIEW,
        icon="analytics",
    )
    yield
    unregister_link("admin:index")


def test_menu_follows_permissions(report_link: None) -> None:
    nav = build_navigation(admin.site, _request(make_user(Permission.ADMIN_PANEL_ACCESS, Permission.REPORTS_VIEW)))

    assert "Test reports" in _items(nav)
    assert str(NavigationGroup.REPORTS.label) in _titles(nav)


def test_menu_hides_entries_without_permission(report_link: None) -> None:
    nav = build_navigation(admin.site, _request(make_user(Permission.ADMIN_PANEL_ACCESS)))

    assert "Test reports" not in _items(nav)
    assert str(NavigationGroup.REPORTS.label) not in _titles(nav)


def test_menu_is_empty_without_panel_access(report_link: None) -> None:
    assert build_navigation(admin.site, _request(make_user(Permission.REPORTS_VIEW))) == []


def test_groups_keep_the_original_order() -> None:
    assert [group.key for group in NavigationGroup] == [
        "student_records",
        "admissions",
        "curriculum",
        "registration",
        "grading",
        "evaluation",
        "assessments",
        "certificates",
        "graduation",
        "reports",
        "lms",
        "reference_data",
        "access",
        "audit",
        "settings",
    ]


def test_group_labels_are_translated() -> None:
    from django.utils import translation

    with translation.override("ko"):
        assert NavigationGroup.ACCESS.label == "사용자와 권한"
    with translation.override("zh-hans"):
        assert NavigationGroup.ACCESS.label == "用户与权限"


# Model admins and custom views on a site of their own (URLs below, pytest ``urls`` marker).
test_site = NinefruitsAdminSite(name="admin")


class UserAdmin(CatalogAdmin):
    permissions = {"view": Permission.USERS_VIEW, "change": Permission.USERS_UPDATE}
    navigation_group = NavigationGroup.ACCESS
    navigation_icon = "person"


class RoleAdmin(ReadOnlyCatalogAdmin):
    permissions = {"view": Permission.ROLES_VIEW}
    navigation_group = NavigationGroup.ACCESS


test_site.register(User, UserAdmin)
test_site.register(Role, RoleAdmin)


def reports_view(request: HttpRequest) -> HttpResponse:
    return HttpResponse("reports page")


test_site.register_view(
    "reports/",
    reports_view,
    name="test_reports",
    permission=Permission.REPORTS_VIEW,
    navigation_group=NavigationGroup.REPORTS,
    label="Reports page",
    icon="analytics",
)

urlpatterns = [
    path("admin/", test_site.urls),
    path("accounts/", include("allauth.urls")),
    path("portal/", include("ninefruits.portal.urls")),
    path("i18n/", include("ninefruits.i18n.urls")),
]


@pytest.fixture
def _test_urls(settings: Any) -> None:
    settings.ROOT_URLCONF = __name__


@pytest.mark.usefixtures("_test_urls")
def test_model_admins_appear_in_their_group_when_viewable() -> None:
    viewer = make_user(Permission.ADMIN_PANEL_ACCESS, Permission.USERS_VIEW)

    nav = build_navigation(test_site, _request(viewer))

    access = next(group for group in nav if group["title"] == str(NavigationGroup.ACCESS.label))
    assert [item["link"] for item in access["items"]] == [reverse("admin:security_user_changelist")]
    assert access["items"][0]["icon"] == "person"


@pytest.mark.usefixtures("_test_urls")
def test_granting_a_permission_adds_the_menu_item() -> None:
    user = make_user(Permission.ADMIN_PANEL_ACCESS)
    assert reverse("admin:security_role_changelist") not in str(build_navigation(test_site, _request(user)))

    role = Role.objects.get(assignments__user=user)
    role.give_permission_to(str(Permission.ROLES_VIEW))
    from ninefruits.security.services.authorization import authorization

    authorization().flush()

    assert reverse("admin:security_role_changelist") in str(build_navigation(test_site, _request(user)))


@pytest.mark.usefixtures("_test_urls")
def test_custom_views_require_their_permission() -> None:
    allowed = signed_in(make_user(Permission.ADMIN_PANEL_ACCESS, Permission.REPORTS_VIEW))
    denied = signed_in(make_user(Permission.ADMIN_PANEL_ACCESS))

    assert allowed.get("/admin/reports/").content == b"reports page"
    assert denied.get("/admin/reports/").status_code == 403
    assert Client().get("/admin/reports/").status_code == 302


@pytest.mark.usefixtures("_test_urls")
def test_custom_views_appear_in_the_menu_for_permitted_users() -> None:
    nav = build_navigation(test_site, _request(make_user(Permission.ADMIN_PANEL_ACCESS, Permission.REPORTS_VIEW)))

    assert "Reports page" in _items(nav)
    assert "/admin/reports/" in str(nav)


@pytest.mark.usefixtures("_test_urls")
def test_catalog_admin_permissions() -> None:
    viewer = make_user(Permission.ADMIN_PANEL_ACCESS, Permission.USERS_VIEW, Permission.ROLES_VIEW)
    request = _request(viewer)
    user_admin = test_site._registry[User]
    role_admin = test_site._registry[Role]

    assert user_admin.has_view_permission(request)
    assert not user_admin.has_change_permission(request)
    assert not user_admin.has_delete_permission(request)
    assert role_admin.has_view_permission(request)
    assert not role_admin.has_add_permission(request)


def test_admins_without_a_group_use_their_apps_group() -> None:
    class AuditLikeAdmin(CatalogAdmin):
        pass

    instance = AuditLikeAdmin(User, test_site)
    AuditLikeAdmin.__module__ = "ninefruits.audit.admin"
    try:
        assert navigation.group_for(instance) == NavigationGroup.ACCESS
    finally:
        AuditLikeAdmin.__module__ = __name__


# -- pages in other languages ---------------------------------------------------------------------


def test_renders_the_dashboard_in_korean_and_chinese() -> None:
    user = administrator()
    client = signed_in(user)

    for locale, dashboard, access in (("ko", "대시보드", "사용자와 권한"), ("zh-hans", "仪表板", "用户与权限")):
        User.objects.filter(pk=user.pk).update(locale=locale)
        response = client.get("/admin/")
        content = response.content.decode()
        assert response.status_code == 200
        assert dashboard in content
        assert access in content  # sidebar group of the user and role admins


def test_dashboard_apps_carry_their_translated_navigation_group() -> None:
    """App headings use the navigation group labels (translated), apps of a group merged."""
    from django.utils import translation

    request = RequestFactory().get("/admin/")
    request.user = administrator()
    with translation.override("ko"):
        apps = admin.site.get_app_list(request)
        names = [str(app["name"]) for app in apps]
        expected = str(NavigationGroup.CURRICULUM.value)
    assert expected in names
    assert expected != "Curriculum and sections"
    assert len(names) == len(set(names))
    assert "Offering" not in names and "Admission" not in names
