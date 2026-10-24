"""Admin (unfold) language menu: the institution's supported locales, posted to the locale
switcher (``UNFOLD["LANGUAGES"]`` in settings)."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest
from django.urls import reverse


def language_navigation(request: HttpRequest) -> list[dict[str, Any]]:
    from ninefruits.institution.services.supported_locales import SupportedLocales

    locales = SupportedLocales()
    return [{"code": code, "name": locales.label(code), "name_local": locales.label(code)} for code in locales.all()]


def language_action(request: HttpRequest) -> str:
    return reverse("i18n:locale-update")
