"""Locale order: user preference, session choice, browser language, institution default
(original ``App\\Http\\Middleware\\SetLocale``).

Runs after ``AuthenticationMiddleware`` and before ``SetDatabaseSessionContextMiddleware``,
which passes ``request.LANGUAGE_CODE`` to PostgreSQL (``app.locale``, read by ``util.i18n``).
Date and number formatting follow the active language (Django ``formats`` and
``ninefruits.i18n.formatting``, the original Carbon/Number locale).
"""

from __future__ import annotations

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.utils import translation
from django.utils.cache import patch_vary_headers

from ninefruits.institution.services.supported_locales import SupportedLocales

SESSION_KEY = "locale"


def supported_locales() -> list[str]:
    return SupportedLocales().all()


def resolve_locale(request: HttpRequest, locales: SupportedLocales | None = None) -> str:
    locales = locales or SupportedLocales()
    supported = locales.all()
    user = getattr(request, "user", None)
    session = getattr(request, "session", None)
    candidates = [
        getattr(user, "locale", None) if user is not None and user.is_authenticated else None,
        session.get(SESSION_KEY) if session is not None else None,
        locales.negotiate(request),
    ]
    return next((c for c in candidates if c is not None and c in supported), None) or locales.default()


class SetLocaleMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        locale = resolve_locale(request)
        translation.activate(locale)
        request.LANGUAGE_CODE = locale
        response = self.get_response(request)
        response.headers.setdefault("Content-Language", locale)
        patch_vary_headers(response, ("Accept-Language",))
        return response
