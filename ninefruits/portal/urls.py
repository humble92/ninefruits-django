"""Portal routes (``/portal/``). Later phases add their screens here."""

from __future__ import annotations

import importlib

from django.urls import URLPattern, path

from .views.dashboard import DashboardView

app_name = "portal"

urlpatterns: list[URLPattern] = [
    path("", DashboardView.as_view(), name="dashboard"),
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
