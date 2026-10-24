"""Portal routes of graduation, included in ``ninefruits.portal.urls`` (names ``portal:...``)."""

from __future__ import annotations

from django.urls import path

from ninefruits.graduation.views.portal import MyGraduationView

urlpatterns = [
    path("graduation/", MyGraduationView.as_view(), name="graduation"),
]
