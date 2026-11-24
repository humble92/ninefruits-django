"""Read-only fields that point to another record link to its admin page only when the user may
open it there; otherwise they show the record's name. (Django and unfold link without checking,
which leads to a page the user cannot see.) Installed in ``AdminPanelConfig.ready``."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest


def can_open(request: HttpRequest, admin_site: Any, model: type, obj: Any) -> bool:
    model_admin = admin_site._registry.get(model)
    if model_admin is None or not model_admin.has_view_or_change_permission(request, obj):
        return False
    return bool(model_admin.get_queryset(request).filter(pk=obj.pk).exists())


def install() -> None:
    from unfold.fields import UnfoldAdminReadonlyField

    original = UnfoldAdminReadonlyField.get_admin_url

    def get_admin_url(self: Any, remote_field: Any, remote_obj: Any) -> Any:
        request = getattr(self.form, "_admin_request", None)
        if request is not None and not can_open(request, self.model_admin.admin_site, remote_field.model, remote_obj):
            return str(remote_obj)
        return original(self, remote_field, remote_obj)

    UnfoldAdminReadonlyField.get_admin_url = get_admin_url
