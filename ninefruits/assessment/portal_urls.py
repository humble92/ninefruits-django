"""Portal routes of the examinations, included in ``ninefruits.portal.urls`` (names ``portal:...``)."""

from __future__ import annotations

from django.urls import path

from ninefruits.assessment.views.portal import MyAssessmentsView

urlpatterns = [
    path("assessments/", MyAssessmentsView.as_view(), name="assessments"),
]
