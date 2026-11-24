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

import inspect
from typing import Any, ClassVar

from django.http import HttpRequest
from django.urls import reverse
from unfold.admin import ModelAdmin

from ninefruits.security.authorization import policy_allows

from .navigation import NavigationGroup


def _call_permission(check: Any, request: HttpRequest, object_id: Any) -> bool:
    """``has_<permission>_permission`` with the row when it takes one (``object_id``)."""
    try:
        parameters = inspect.signature(check).parameters
    except TypeError, ValueError:
        parameters = {}
    takes_row = len(parameters) > 1 or any(p.kind is p.VAR_POSITIONAL for p in parameters.values())
    return bool(check(request, object_id) if takes_row else check(request))


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

    def policy_allows(self, request: HttpRequest, ability: str, target: Any) -> bool:
        """The model policy's ``ability`` for ``target``: an instance, or the model class for
        ``view_any``/``create`` (original ``Gate::allows('create', Model::class)``)."""
        return policy_allows(request.user, ability, target)

    def get_queryset(self, request: HttpRequest) -> Any:
        queryset = super().get_queryset(request)  # type: ignore[misc]
        visible_to = getattr(queryset, "visible_to", None)
        return visible_to(request.user) if visible_to else queryset

    def render_change_form(
        self, request: HttpRequest, context: dict[str, Any], add: bool = False, change: bool = False, **kwargs: Any
    ) -> Any:
        # A user who may open this record but not the list gets no link to the list (it would
        # answer 403): no "Close" button (templates/admin/change_form.html) and the list part of
        # the page header as text (templates/unfold/helpers/header_title.html).
        hide_list = not add and not self.has_view_or_change_permission(request)  # type: ignore[attr-defined]
        context["hide_close"] = hide_list
        if hide_list:
            opts = self.model._meta  # type: ignore[attr-defined]
            request.admin_hidden_list_url = reverse(  # type: ignore[attr-defined]
                f"{self.admin_site.name}:{opts.app_label}_{opts.model_name}_changelist"  # type: ignore[attr-defined]
            )
        return super().render_change_form(request, context, add=add, change=change, **kwargs)  # type: ignore[misc]

    def row_action_allowed(self, request: HttpRequest, action_name: str, object_id: Any) -> bool:
        """Whether the row action ``action_name`` (the URL name, ``<app>_<model>_<action>``)
        applies to the row ``object_id``: unfold filters row actions per request only, so the
        ``has_<permission>_permission(request, object_id)`` checks run here for every row."""
        for row_action in self.get_actions_row(request):  # type: ignore[attr-defined]
            if row_action.action_name != action_name:
                continue
            for permission in getattr(row_action.method, "allowed_permissions", ()):
                if "." in permission:
                    if not request.user.has_perm(permission):
                        return False
                elif not _call_permission(getattr(self, f"has_{permission}_permission"), request, object_id):
                    return False
            return True
        return True

    def row_object(self, request: HttpRequest, object_id: Any) -> Any:
        """The visible record ``object_id`` for per-row permission checks, or ``None``
        (memoised for the request, as every row action of a row asks for it)."""
        cache: dict[tuple[str, str], Any] = request.__dict__.setdefault("_row_objects", {})
        key = (self.model._meta.label, str(object_id))  # type: ignore[attr-defined]
        if key not in cache:
            cache[key] = self.get_queryset(request).filter(pk=object_id).first()
        return cache[key]

    def get_form(self, request: HttpRequest, obj: Any = None, change: bool = False, **kwargs: Any) -> Any:
        # On a view-only change page Django excludes every field from the form, so custom
        # forms that adjust ``self.fields[...]`` in ``__init__`` raise KeyError. The page shows
        # all fields read-only anyway and Django refuses a POST without the change
        # permission, so keep the fields in the form.
        if change and obj is not None and not self.has_change_permission(request, obj):
            change = False
        form = super().get_form(request, obj, change=change, **kwargs)  # type: ignore[misc]
        # A new class per call: read-only related-record links check the user's access with it
        # (ninefruits.adminpanel.readonly_links).
        form._admin_request = request
        return form

    def get_formset(self, request: HttpRequest, obj: Any = None, **kwargs: Any) -> Any:
        """Inlines: the same request on the formset's (new) form class as ``get_form``."""
        formset = super().get_formset(request, obj, **kwargs)  # type: ignore[misc]
        formset.form._admin_request = request
        return formset


class CatalogAdmin(CatalogPermissionMixin, ModelAdmin):
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
