"""Portal routes of the certificates, included in ``ninefruits.portal.urls`` (names ``portal:...``)."""

from __future__ import annotations

from django.urls import path

from ninefruits.certificate.views.portal import MyCertificatesView

urlpatterns = [
    path("certificates/", MyCertificatesView.as_view(), name="certificates"),
]
