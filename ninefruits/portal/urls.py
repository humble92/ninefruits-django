"""Portal routes (``/portal/``). Later phases add their screens here."""

from __future__ import annotations

import importlib

from django.urls import URLPattern, URLResolver, include, path

from .views.dashboard import DashboardView

app_name = "portal"

urlpatterns: list[URLPattern | URLResolver] = [
    path("", DashboardView.as_view(), name="dashboard"),
    # Course catalog, section pages, syllabus editor, teaching (Phase 4).
    path("", include("ninefruits.offering.portal_urls")),
    # My records, my details, advisees (Phase 2).
    path("", include("ninefruits.person.portal_urls")),
    # Applications (Phase 3).
    path("", include("ninefruits.admission.portal_urls")),
    # Registration and the student timetable (Phase 5).
    path("", include("ninefruits.registration.portal_urls")),
    # Grade entry, my grades and the grade report (Phase 6).
    path("", include("ninefruits.grading.portal_urls")),
]

# Security settings page (two-factor, sign-in methods), built by the security work.
try:
    _security = importlib.import_module("ninefruits.portal.views.security")
except ModuleNotFoundError as error:  # pragma: no cover - until the security page exists
    if error.name != "ninefruits.portal.views.security":
        raise
    _security = None  # type: ignore[assignment]

if _security is not None:
    _security_view = getattr(_security, "SecurityView", None)
    urlpatterns.append(
        path(
            "security/",
            _security_view.as_view() if _security_view is not None else _security.security,
            name="security",
        )
    )
