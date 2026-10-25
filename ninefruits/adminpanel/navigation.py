"""Admin sidebar (original ``App\\Filament\\Admin\\NavigationGroup`` + Filament navigation).

The sidebar is built for each request from what the user may open:

- every ``ModelAdmin`` registered on the admin site whose ``has_view_permission`` is true for the
  user, in its ``navigation_group`` (default: the group of its Ninefruits app, ``APP_GROUPS``),
  labelled ``navigation_label`` or the model's plural name, with ``navigation_icon`` and
  ``navigation_order``;
- links registered with :func:`register_link` (custom admin views of other apps: settings
  pages, reports, timetables) whose ``permission`` the user holds.

Groups appear in the order of :class:`NavigationGroup` (the original enum order). Labels are
lazy so they are translated when the menu renders, after the locale middleware has run.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse
from django.utils.translation import pgettext_lazy

if TYPE_CHECKING:
    from django.contrib.admin import AdminSite


class NavigationGroup(Enum):
    """Admin panel navigation groups, in display order."""

    STUDENT_RECORDS = pgettext_lazy("admin", "Students and staff")
    ADMISSIONS = pgettext_lazy("admin", "Admissions")
    CURRICULUM = pgettext_lazy("admin", "Curriculum and sections")
    REGISTRATION = pgettext_lazy("admin", "Registration")
    GRADING = pgettext_lazy("admin", "Grades")
    EVALUATION = pgettext_lazy("admin", "Course evaluation")
    ASSESSMENTS = pgettext_lazy("admin", "Examinations")
    CERTIFICATES = pgettext_lazy("admin", "Certificates")
    GRADUATION = pgettext_lazy("admin", "Graduation")
    REPORTS = pgettext_lazy("admin", "Reports")
    LMS = pgettext_lazy("admin", "LMS integration")
    REFERENCE_DATA = pgettext_lazy("admin", "Reference data")
    ACCESS = pgettext_lazy("admin", "Users and access")
    AUDIT = pgettext_lazy("admin", "Audit")
    SETTINGS = pgettext_lazy("admin", "Settings")

    @property
    def label(self) -> str:
        return str(self.value)

    @property
    def key(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class NavigationLink:
    """A sidebar entry that is not a model changelist (a custom admin view)."""

    group: NavigationGroup
    label: Any
    url_name: str
    permission: str | Callable[[HttpRequest], bool] | None = None
    icon: str = "chevron_right"
    order: int = 100
    url_kwargs: dict[str, Any] = field(default_factory=dict)

    def is_allowed(self, request: HttpRequest) -> bool:
        if self.permission is None:
            return True
        if callable(self.permission):
            return bool(self.permission(request))
        return bool(request.user.has_perm(str(self.permission)))


_links: dict[str, NavigationLink] = {}

#: Group of a Ninefruits app's admins that do not set ``navigation_group`` themselves
#: (the original resources' ``$navigationGroup`` per context).
APP_GROUPS: dict[str, NavigationGroup] = {
    "person": NavigationGroup.STUDENT_RECORDS,
    "admission": NavigationGroup.ADMISSIONS,
    "curriculum": NavigationGroup.CURRICULUM,
    "offering": NavigationGroup.CURRICULUM,
    "attendance": NavigationGroup.CURRICULUM,
    "registration": NavigationGroup.REGISTRATION,
    "grading": NavigationGroup.GRADING,
    "evaluation": NavigationGroup.EVALUATION,
    "assessment": NavigationGroup.ASSESSMENTS,
    "certificate": NavigationGroup.CERTIFICATES,
    "graduation": NavigationGroup.GRADUATION,
    "reporting": NavigationGroup.REPORTS,
    "lms": NavigationGroup.LMS,
    "institution": NavigationGroup.REFERENCE_DATA,
    "organization": NavigationGroup.REFERENCE_DATA,
    "facility": NavigationGroup.REFERENCE_DATA,
    "term": NavigationGroup.REFERENCE_DATA,
    "importing": NavigationGroup.REFERENCE_DATA,
    "security": NavigationGroup.ACCESS,
    "audit": NavigationGroup.AUDIT,
    "pii": NavigationGroup.AUDIT,
    "appsettings": NavigationGroup.SETTINGS,
    "settings": NavigationGroup.SETTINGS,
}


def group_for(model_admin: Any) -> NavigationGroup | None:
    """``navigation_group`` of the admin, else the default group of its Ninefruits app. Admins of
    Django and third party apps without ``navigation_group`` are not in the sidebar."""
    group = getattr(model_admin, "navigation_group", None)
    if isinstance(group, NavigationGroup):
        return group
    module = type(model_admin).__module__
    if not module.startswith("ninefruits."):
        return None
    return APP_GROUPS.get(model_admin.model._meta.app_label)


def register_link(
    *,
    group: NavigationGroup,
    label: Any,
    url_name: str,
    permission: str | Callable[[HttpRequest], bool] | None = None,
    icon: str = "chevron_right",
    order: int = 100,
    url_kwargs: dict[str, Any] | None = None,
) -> NavigationLink:
    """Adds a custom admin view to the sidebar. Registering the same ``url_name`` again
    replaces the entry (safe to call from ``AppConfig.ready``)."""
    link = NavigationLink(group, label, url_name, permission, icon, order, url_kwargs or {})
    _links[url_name] = link
    return link


def unregister_link(url_name: str) -> None:
    _links.pop(url_name, None)


def registered_links() -> list[NavigationLink]:
    return list(_links.values())


def _model_items(site: AdminSite, request: HttpRequest) -> list[tuple[NavigationGroup, int, dict[str, Any]]]:
    items = []
    for model, model_admin in site._registry.items():
        group = group_for(model_admin)
        if group is None or getattr(model_admin, "navigation_hidden", False):
            continue
        if not model_admin.has_view_permission(request):
            continue
        opts = model._meta
        try:
            link = reverse(f"{site.name}:{opts.app_label}_{opts.model_name}_changelist")
        except NoReverseMatch:
            continue
        label = getattr(model_admin, "navigation_label", None) or opts.verbose_name_plural
        item = {
            "title": str(label)[:1].upper() + str(label)[1:],
            "icon": getattr(model_admin, "navigation_icon", "table_rows"),
            "link": link,
        }
        # ``navigation_badge(request) -> str | None``: e.g. the number of pending requests.
        badge = getattr(model_admin, "navigation_badge", None)
        if callable(badge):
            value = badge(request)
            if value:
                item["badge"] = str(value)
        items.append((group, int(getattr(model_admin, "navigation_order", 100)), item))
    return items


def _link_items(site: AdminSite, request: HttpRequest) -> list[tuple[NavigationGroup, int, dict[str, Any]]]:
    items = []
    for entry in _links.values():
        if not entry.is_allowed(request):
            continue
        try:
            link = reverse(entry.url_name, kwargs=entry.url_kwargs or None)
        except NoReverseMatch:
            continue
        items.append((entry.group, entry.order, {"title": str(entry.label), "icon": entry.icon, "link": link}))
    return items


#: Sidebar providers of other apps: (module, function, group). ``function(site_name)`` returns
#: unfold items (``title``, ``icon``, ``link``, optional ``permission(request) -> bool``).
SIDEBAR_PROVIDERS: tuple[tuple[str, str, NavigationGroup], ...] = (
    ("ninefruits.settings.admin_views", "sidebar_items", NavigationGroup.SETTINGS),
)


def _provider_items(site: AdminSite, request: HttpRequest) -> list[tuple[NavigationGroup, int, dict[str, Any]]]:
    items = []
    for module_name, function_name, group in SIDEBAR_PROVIDERS:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            if error.name and module_name.startswith(error.name):
                continue
            raise
        provider = getattr(module, function_name, None)
        if provider is None:
            continue
        for position, item in enumerate(provider(site.name)):
            permission = item.get("permission")
            if callable(permission) and not permission(request):
                continue
            entry = {"title": str(item["title"]), "icon": item.get("icon") or "settings", "link": str(item["link"])}
            items.append((group, position, entry))
    return items


def build_navigation(site: AdminSite, request: HttpRequest) -> list[dict[str, Any]]:
    """unfold ``SIDEBAR.navigation`` structure for ``request.user``. Empty groups are left out."""
    if not site.has_permission(request):
        return []
    grouped: dict[NavigationGroup, list[tuple[int, str, dict[str, Any]]]] = {}
    for group, order, item in [
        *_model_items(site, request),
        *_link_items(site, request),
        *_provider_items(site, request),
    ]:
        grouped.setdefault(group, []).append((order, item["title"], item))

    navigation: list[dict[str, Any]] = [
        {
            "title": "",
            "items": [
                {
                    "title": str(pgettext_lazy("admin", "Dashboard")),
                    "icon": "dashboard",
                    "link": reverse(f"{site.name}:index"),
                }
            ],
        }
    ]
    for group in NavigationGroup:
        entries = grouped.get(group)
        if not entries:
            continue
        entries.sort(key=lambda entry: (entry[0], entry[1]))
        navigation.append(
            {
                "title": group.label,
                "separator": True,
                "collapsible": True,
                "items": [item for _, _, item in entries],
            }
        )
    return navigation


def sidebar_navigation(request: HttpRequest) -> list[dict[str, Any]]:
    """Entry point referenced by ``UNFOLD["SIDEBAR"]["navigation"]``."""
    from django.contrib import admin

    return build_navigation(admin.site, request)
