"""Layout components: the portal header navigation and the two-factor reminder (original Blade
component ``mfa-reminder``). The locale switcher is ``{% load nf_i18n %}{% locale_switcher %}``."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django import template
from django.urls import NoReverseMatch, reverse
from django.utils.translation import pgettext

from ninefruits.i18n.formatting import format_ll
from ninefruits.portal import menu

register = template.Library()

SECURITY_URL_NAME = "portal:security"


@register.inclusion_tag("portal/partials/navigation.html", takes_context=True)
def portal_navigation(context: template.Context) -> dict[str, Any]:
    request = context["request"]
    return {"items": menu.items_for(request), "request": request}


def reminder_message(reminder: dict[str, Any] | None) -> str | None:
    """Text of the two-factor reminder, or None when there is nothing to show."""
    if not reminder:
        return None
    deadline = reminder.get("deadline")
    if reminder.get("required") and deadline:
        if isinstance(deadline, str):
            deadline = datetime.fromisoformat(deadline)
        return pgettext(
            "security",
            "Two-factor authentication is required for your account. Please set it up by %(date)s.",
        ) % {"date": format_ll(deadline)}
    return pgettext("security", "We recommend enabling two-factor authentication for your account.")


@register.inclusion_tag("portal/partials/mfa_reminder.html", takes_context=True)
def mfa_reminder(context: template.Context) -> dict[str, Any]:
    """Shown on every page except the security page itself (EnforceMfaPolicy sets
    ``request.mfa_reminder = {"required": bool, "deadline": datetime | None}``)."""
    request = context.get("request")
    reminder = getattr(request, "mfa_reminder", None) if request is not None else None
    view_name = getattr(getattr(request, "resolver_match", None), "view_name", None)
    message = None if view_name == SECURITY_URL_NAME else reminder_message(reminder)
    try:
        security_url = reverse(SECURITY_URL_NAME)
    except NoReverseMatch:
        security_url = None
    return {"message": message, "security_url": security_url}
