"""Callables referenced by ``settings.UNFOLD`` (original ``AdminPanelProvider::panel``)."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse
from django.utils import translation
from django.utils.translation import pgettext

# Tailwind indigo (original panel colour ``Color::Indigo``).
INDIGO = {
    "50": "oklch(96.2% .018 272.314)",
    "100": "oklch(93% .034 272.788)",
    "200": "oklch(87% .065 274.039)",
    "300": "oklch(78.5% .115 274.713)",
    "400": "oklch(67.3% .182 276.935)",
    "500": "oklch(58.5% .233 277.117)",
    "600": "oklch(51.1% .262 276.966)",
    "700": "oklch(45.7% .24 277.023)",
    "800": "oklch(39.8% .195 277.366)",
    "900": "oklch(35.9% .144 278.697)",
    "950": "oklch(25.7% .09 281.288)",
}


def institution_name(locale: str | None = None) -> str:
    """Institution name in the current language, then the fallback language, then APP_NAME
    (original ``brandName``)."""
    from ninefruits.settings.groups.base import MissingSettings
    from ninefruits.settings.groups.institution import InstitutionSettings

    try:
        names = InstitutionSettings.load().name
    except MissingSettings:
        names = {}
    locale = locale or translation.get_language() or settings.LANGUAGE_CODE
    fallback = getattr(settings, "FALLBACK_LANGUAGE", settings.LANGUAGE_CODE)
    return str(names.get(locale) or names.get(fallback) or settings.APP_NAME)


def site_title(request: HttpRequest) -> str:
    return institution_name()


def environment(request: HttpRequest) -> list[str] | None:
    """Environment badge outside production."""
    env = getattr(settings, "DJANGO_ENV", "production")
    if env == "production":
        return None
    return [str(env), "warning" if env != "testing" else "info"]


def primary_colors(request: HttpRequest) -> dict[str, str]:
    return dict(INDIGO)


def _url(name: str, fallback: str) -> str:
    try:
        return reverse(name)
    except NoReverseMatch:
        return fallback


def account_links(request: HttpRequest) -> list[dict[str, Any]]:
    """User menu items of the original panel: two-factor settings and the portal."""
    return [
        {
            "title": pgettext("security", "Two-factor authentication"),
            "link": lambda request: _url("portal:security", "/portal/security/"),
        },
        {"title": pgettext("admin", "Portal"), "link": lambda request: _url("portal:dashboard", "/portal/")},
    ]


def dashboard(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    """Dashboard widgets. The original dashboard has only Filament's account widget."""
    user = request.user
    context.update(
        {
            "account_name": str(user),
            "account_email": getattr(user, "email", ""),
            "portal_url": _url("portal:dashboard", "/portal/"),
        }
    )
    return context
