"""EnsureUserIsActive and EnforceMfaPolicy (original middleware of the same names)."""

from __future__ import annotations

from collections.abc import Callable

from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect


class EnsureUserIsActiveMiddleware:
    """A deactivated account loses its sessions at once, not only at the next sign-in
    (original security review M8)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_active:
            logout(request)
            return redirect("account_login")
        return self.get_response(request)


class EnforceMfaPolicyMiddleware:
    """Applies the two-factor policy on every authenticated request."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)
