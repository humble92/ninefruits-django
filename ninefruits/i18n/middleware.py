"""Locale order: user preference, session choice, browser language, institution default."""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils import translation

SESSION_KEY = "locale"


def supported_locales() -> list[str]:
    return [code for code, _ in settings.LANGUAGES]


class SetLocaleMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        supported = supported_locales()
        user = getattr(request, "user", None)
        candidates = [
            getattr(user, "locale", None) if user is not None and user.is_authenticated else None,
            request.session.get(SESSION_KEY) if hasattr(request, "session") else None,
            translation.get_language_from_request(request),
        ]
        locale = next((c for c in candidates if c in supported), settings.LANGUAGE_CODE)
        translation.activate(locale)
        request.LANGUAGE_CODE = locale  # type: ignore[attr-defined]
        response = self.get_response(request)
        response.headers.setdefault("Content-Language", locale)
        return response
