"""Error pages of browser screens (400, 403, CSRF failure, 404, 429, 500, 503).

One template (``errors/error.html``) shows every error with its code, icon, title and message.
Signed-in users keep the admin or portal layout; 400 and 500 use a self-contained layout that
needs neither the database nor built assets, since either may be what failed. Every page shows
the request id (``X-Request-Id``), which the logs carry, so a reported problem can be traced.

Wiring: ``handler400``/``403``/``404``/``500`` and ``handler429`` (allauth rate limits) in
``config.urls``, ``CSRF_FAILURE_VIEW``, and ``ErrorPageMiddleware`` for ``Http404`` and
``PermissionDenied`` raised by views (so they look the same with ``DEBUG`` on). API requests
(``/api/``, JSON clients) get a short JSON body instead."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import loader
from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

API_PREFIX = "/api/"
STANDALONE_LAYOUT = "errors/standalone.html"


@dataclass(frozen=True)
class ErrorKind:
    status: int
    title: Any
    message: Any
    icon: str  # an icon of errors/icon.html
    color: str
    tint: str
    standalone: bool = False  # render without the database (no layout, no context processors)


ERRORS: dict[str, ErrorKind] = {
    "bad_request": ErrorKind(
        400,
        _("Bad request"),
        _("The request could not be processed. Check the address and try again."),
        "warning",
        "#b45309",
        "#fef3c7",
        standalone=True,
    ),
    "permission_denied": ErrorKind(
        403,
        _("No permission"),
        _("You do not have permission to view this page or to perform this action."),
        "lock",
        "#b91c1c",
        "#fee2e2",
    ),
    "csrf_failure": ErrorKind(
        403,
        _("The page has expired"),
        _("The form was open for too long or your session changed. Reload the page and try again."),
        "refresh",
        "#1d4ed8",
        "#dbeafe",
    ),
    "not_found": ErrorKind(
        404,
        _("No information to show"),
        _("There is no information matching your request."),
        "search",
        "#475569",
        "#e2e8f0",
    ),
    "too_many_requests": ErrorKind(
        429,
        _("Too many requests"),
        _("Wait a minute and try again."),
        "clock",
        "#b45309",
        "#fef3c7",
    ),
    "server_error": ErrorKind(
        500,
        _("Something went wrong"),
        _(
            "An unexpected error occurred. Try again later. If it keeps happening, tell the "
            "administrator the reference below."
        ),
        "error",
        "#b91c1c",
        "#fee2e2",
        standalone=True,
    ),
    "unavailable": ErrorKind(
        503,
        _("Temporarily unavailable"),
        _("The service is temporarily unavailable. Try again later."),
        "pause",
        "#4338ca",
        "#e0e7ff",
    ),
}


def is_browser_request(request: HttpRequest) -> bool:
    if request.path.startswith(API_PREFIX):
        return False
    accept = request.headers.get("Accept", "")
    return not ("application/json" in accept and "text/html" not in accept)


def _layout(request: HttpRequest) -> tuple[str, str, dict[str, Any]]:
    """Layout template, home URL and extra context for the signed-in state of ``request``."""
    from django.contrib import admin

    user = getattr(request, "user", None)
    signed_in = bool(user is not None and user.is_authenticated)
    try:
        if request.path.startswith("/admin/") and signed_in and admin.site.has_permission(request):
            return "admin/base_site.html", reverse("admin:index"), dict(admin.site.each_context(request))
        if signed_in:
            return "portal/base.html", reverse("portal:dashboard"), {}
        return "layouts/guest.html", reverse("account_login"), {}
    except NoReverseMatch:  # a URLconf without these pages (tests of a single app)
        return STANDALONE_LAYOUT, "/", {}


def error_page(request: HttpRequest, kind: str, message: Any = None) -> HttpResponse:
    """The error page ``kind`` (a key of ``ERRORS``); ``message`` replaces the standard text."""
    error = ERRORS[kind]
    text = message if message is not None else error.message
    if not is_browser_request(request):
        return JsonResponse({"detail": str(text)}, status=error.status)
    context: dict[str, Any] = {
        "status": error.status,
        "error": error,
        "title": error.title,
        "message": text,
        "request_id": getattr(request, "request_id", ""),
    }
    if error.standalone:
        context.update(layout=STANDALONE_LAYOUT, home_url="/")
        # No request: context processors (site name, user) would query the database.
        body = loader.get_template("errors/error.html").render(context)
        return HttpResponse(body, status=error.status)
    layout, home_url, extra = _layout(request)
    context.update(extra)
    context.update(layout=layout, home_url=home_url, title=error.title)
    return render(request, "errors/error.html", context, status=error.status)


# -- Django handlers (config.urls, settings.CSRF_FAILURE_VIEW) -------------------------------------
def bad_request(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    return error_page(request, "bad_request")


def permission_denied(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    return error_page(request, "permission_denied")


def csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    logger.info("CSRF verification failed: %s", reason)
    return error_page(request, "csrf_failure")


def page_not_found(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    return error_page(request, "not_found")


def too_many_requests(request: HttpRequest, exception: Exception | None = None) -> HttpResponse:
    return error_page(request, "too_many_requests")


def server_error(request: HttpRequest) -> HttpResponse:
    try:
        return error_page(request, "server_error")
    except Exception:  # the error page itself must not fail
        logger.exception("The error page could not be rendered.")
        return HttpResponse("Server Error (500)", status=500, content_type="text/plain")
