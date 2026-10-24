"""``{% load nf_i18n %}``: locale switcher and locale aware formatting filters."""

from __future__ import annotations

from typing import Any

from django import template
from django.utils import translation

from ninefruits.i18n import formatting
from ninefruits.i18n.translation import translate

register = template.Library()


@register.inclusion_tag("i18n/locale_switcher.html", takes_context=True)
def locale_switcher(context: template.Context) -> dict[str, Any]:
    """Language menu (original ``x-locale-switcher``)."""
    from ninefruits.institution.services.supported_locales import SupportedLocales

    request = context.get("request")
    return {
        "request": request,
        "csrf_token": context.get("csrf_token"),
        "csp_nonce": context.get("csp_nonce"),
        "locales": SupportedLocales().choices(),
        "current": translation.get_language(),
        "next": request.get_full_path() if request is not None else "/",
    }


@register.filter
def ll(value: Any) -> str:
    return formatting.format_ll(value)


@register.filter
def lll(value: Any) -> str:
    return formatting.format_lll(value)


@register.filter
def ll_ddd(value: Any) -> str:
    return formatting.format_ll_ddd(value)


@register.filter
def number(value: Any, decimals: int | None = None) -> str:
    return formatting.format_number(value, decimals=decimals)


@register.filter
def percent(value: Any) -> str:
    return formatting.format_percent(value)


@register.filter
def i18n(value: Any, language: str | None = None) -> str:
    """A translatable dict in the active (or given) language: ``{{ settings.name|i18n }}``."""
    return translate(value, language) or ""
