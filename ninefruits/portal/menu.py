"""Portal navigation (original ``components/layouts/portal.blade.php`` header).

Items are shown by persona and permission. Later phases add their pages from
``AppConfig.ready()``::

    from ninefruits.portal import menu
    from ninefruits.security.enums import Persona

    menu.register("records", _("My records"), "portal:records", order=20,
                  personas={Persona.STUDENT, Persona.ALUMNI})

``personas``: shown when the user has any of them. ``permission``: shown when the user holds
it. ``visible``: any other condition (``request -> bool``). All given conditions must hold.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse
from django.utils.translation import pgettext_lazy

from .access import persona_values


@dataclass(frozen=True)
class MenuItem:
    key: str
    label: Any
    url_name: str
    order: int = 100
    personas: frozenset[str] | None = None
    permission: str | None = None
    visible: Callable[[HttpRequest], bool] | None = None

    def is_visible(self, request: HttpRequest) -> bool:
        user = request.user
        if not user.is_authenticated:
            return False
        if self.personas is not None and not (self.personas & persona_values(request)):
            return False
        if self.permission is not None and not user.has_perm(self.permission):
            return False
        return self.visible is None or bool(self.visible(request))


_items: dict[str, MenuItem] = {}


def register(
    key: str,
    label: Any,
    url_name: str,
    *,
    order: int = 100,
    personas: Iterable[Any] | None = None,
    permission: str | None = None,
    visible: Callable[[HttpRequest], bool] | None = None,
) -> MenuItem:
    """Adds (or replaces, by ``key``) a portal menu item."""
    item = MenuItem(
        key=key,
        label=label,
        url_name=url_name,
        order=order,
        personas=frozenset(str(getattr(p, "value", p)) for p in personas) if personas is not None else None,
        permission=str(permission) if permission is not None else None,
        visible=visible,
    )
    _items[key] = item
    return item


def unregister(key: str) -> None:
    _items.pop(key, None)


def registered() -> list[MenuItem]:
    return sorted(_items.values(), key=lambda item: (item.order, item.key))


def items_for(request: HttpRequest) -> list[dict[str, Any]]:
    """Menu entries for the current user: ``label``, ``url``, ``active``, ``key``."""
    current = getattr(getattr(request, "resolver_match", None), "view_name", None)
    entries = []
    for item in registered():
        if not item.is_visible(request):
            continue
        try:
            url = reverse(item.url_name)
        except NoReverseMatch:
            continue
        entries.append({"key": item.key, "label": str(item.label), "url": url, "active": current == item.url_name})
    return entries


def _register_defaults() -> None:
    from ninefruits.security.enums import Permission

    register("dashboard", pgettext_lazy("portal", "Home"), "portal:dashboard", order=0)
    register("security", pgettext_lazy("portal", "Security"), "portal:security", order=900)
    register(
        "admin",
        pgettext_lazy("portal", "Administration"),
        "admin:index",
        order=1000,
        permission=Permission.ADMIN_PANEL_ACCESS,
    )


_register_defaults()
