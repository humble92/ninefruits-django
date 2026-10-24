"""Admin panel time zone (original ``FilamentTimezone::set(institution timezone)``, ADR 0006):
times are shown and entered in the institution time zone and stored in UTC. Wall-clock values
(``time`` columns such as class periods) are not converted."""

from __future__ import annotations

from collections.abc import Callable
from zoneinfo import ZoneInfo

from django.http import HttpRequest, HttpResponse
from django.urls import NoReverseMatch, reverse
from django.utils import timezone


class AdminTimezoneMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            prefix = reverse("admin:index")
        except NoReverseMatch:  # a URL configuration without the admin (tests)
            return self.get_response(request)
        if not request.path.startswith(prefix):
            return self.get_response(request)
        from ninefruits.settings.groups.base import MissingSettings
        from ninefruits.settings.groups.institution import InstitutionSettings

        try:
            zone = ZoneInfo(InstitutionSettings.load().timezone)
        except MissingSettings:
            return self.get_response(request)
        with timezone.override(zone):
            return self.get_response(request)
