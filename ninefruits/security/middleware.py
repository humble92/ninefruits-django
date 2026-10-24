"""EnsureUserIsActive and EnforceMfaPolicy (original middleware of the same names)."""

from __future__ import annotations

from collections.abc import Callable
from fnmatch import fnmatch
from typing import Any

from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _

from ninefruits.security.enums import MfaRequirement


class EnsureUserIsActiveMiddleware:
    """A deactivated account loses its sessions at once, not only at the next sign-in
    (security review M8)."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_active:
            logout(request)
            messages.error(request, _("This account has been deactivated. Contact the administrator."))
            return redirect("account_login")
        return self.get_response(request)


class EnforceMfaPolicyMiddleware:
    """Applies the two-factor policy on every authenticated request, so a policy change takes
    effect immediately. A user who must enroll can only reach ``ALLOWED_ROUTES``; JSON requests
    get 403, pages redirect to the portal security page. Otherwise a reminder is put on the
    request (``request.mfa_reminder``) for the layouts."""

    #: URL names a user who must enroll can still reach (original: portal.security,
    #: two-factor.*, password.confirm*, logout, locale.update).
    ALLOWED_ROUTES = (
        "portal:security",
        "portal:security-*",
        "security:two_factor_*",
        "mfa_reauthenticate",
        "account_reauthenticate",
        "account_logout",
        "i18n:locale-update",
        "admin:logout",
    )

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_view(
        self, request: HttpRequest, view_func: Callable[..., Any], view_args: Any, view_kwargs: Any
    ) -> HttpResponse | None:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return None
        from ninefruits.security.services.mfa_policy import MfaPolicy

        policy = MfaPolicy()
        requirement = policy.requirement_for(user)
        if requirement == MfaRequirement.NONE or policy.is_enrolled(user):
            return None
        if policy.must_enroll_now(user):
            match = request.resolver_match
            view_name = match.view_name if match is not None else ""
            if any(fnmatch(view_name, pattern) for pattern in self.ALLOWED_ROUTES):
                return None
            message = _("Two-factor authentication is required for your account. Please set it up to continue.")
            if _expects_json(request):
                raise PermissionDenied(message)
            messages.warning(request, message)
            if request.headers.get("HX-Request"):
                response = HttpResponse(status=204)
                response["HX-Redirect"] = reverse("portal:security")
                return response
            return redirect("portal:security")
        required = requirement == MfaRequirement.REQUIRED
        request.mfa_reminder = {  # type: ignore[attr-defined]
            "required": required,
            "deadline": policy.grace_ends_at(user) if required else None,
        }
        return None


def _expects_json(request: HttpRequest) -> bool:
    accept = request.headers.get("Accept", "")
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or ("json" in accept and "html" not in accept)
        or request.path.startswith("/api/")
    )
