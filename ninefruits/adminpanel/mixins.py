"""Common admin behaviour (porting-plan 9: Filament Resource -> unfold ModelAdmin).

    @admin.register(Building)
    class BuildingAdmin(CatalogAdmin):
        permissions = {"view": Permission.REFERENCE_DATA_VIEW, "change": Permission.FACILITIES_MANAGE}

``permissions`` maps Django admin actions (view, add, change, delete) to catalog permissions;
a missing key means the action is not allowed (``view`` defaults to the ``change`` permission).
``get_queryset`` always goes through ``visible_to(request.user)``.

Sidebar (``ninefruits.adminpanel.navigation``): ``navigation_group`` (a ``NavigationGroup``;
default: the group of the model's app), ``navigation_label`` (default: the model's plural
name), ``navigation_icon`` (Material Symbols name) and ``navigation_order``."""

from __future__ import annotations

from typing import Any, ClassVar

from django.http import HttpRequest
from unfold.admin import ModelAdmin

from .navigation import NavigationGroup


class CatalogPermissionMixin:
    permissions: ClassVar[dict[str, str]] = {}
    navigation_group: ClassVar[NavigationGroup | None] = None
    navigation_label: ClassVar[Any] = None
    navigation_icon: ClassVar[str] = "table_rows"
    navigation_order: ClassVar[int] = 100

    def _allowed(self, request: HttpRequest, action: str, obj: Any = None) -> bool:
        permission = self.permissions.get(action) or (self.permissions.get("change") if action == "view" else None)
        return bool(permission) and request.user.has_perm(str(permission), obj)

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "view", obj) or self._allowed(request, "change", obj)

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return self._allowed(request, "add") or self._allowed(request, "change")

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "change", obj)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "delete", obj)

    def has_module_permission(self, request: HttpRequest) -> bool:
        return self.has_view_permission(request)

    def get_queryset(self, request: HttpRequest) -> Any:
        queryset = super().get_queryset(request)  # type: ignore[misc]
        visible_to = getattr(queryset, "visible_to", None)
        return visible_to(request.user) if visible_to else queryset


class CatalogAdmin(CatalogPermissionMixin, ModelAdmin):  # type: ignore[misc]
    pass


class ReadOnlyCatalogAdmin(CatalogAdmin):
    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "view", obj)
