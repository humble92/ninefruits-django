"""Row actions of a change list, filtered for each row (see
``CatalogPermissionMixin.row_action_allowed``)."""

from __future__ import annotations

from typing import Any

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def allowed_row_actions(context: template.Context, actions: list[dict[str, Any]] | None, instance_pk: Any) -> list[Any]:
    if not actions:
        return []
    request = getattr(context, "request", None) or context.get("request")
    cl = context.get("cl")
    model_admin = getattr(cl, "model_admin", None)
    check = getattr(model_admin, "row_action_allowed", None)
    if request is None or check is None:
        return list(actions)
    return [action for action in actions if check(request, action["raw_path"].split(":", 1)[-1], instance_pk)]


@register.inclusion_tag("admin/submit_line.html", takes_context=True)
def catalog_submit_row(context: template.Context) -> dict[str, Any]:
    """Django's ``submit_row`` without the "Close" button (a link to the list) when the page sets
    ``hide_close``: a user who may open the record but not the list (``CatalogPermissionMixin``)."""
    from django.contrib.admin.templatetags.admin_modify import submit_row

    values: dict[str, Any] = {str(key): value for key, value in submit_row(context).flatten().items()}  # type: ignore[arg-type]
    if context.get("hide_close"):
        values["show_close"] = False
    return values
