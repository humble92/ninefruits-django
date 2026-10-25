"""Portal routes of the course evaluation, included in ``ninefruits.portal.urls`` (names
``portal:...``)."""

from __future__ import annotations

from django.urls import path

from ninefruits.evaluation.views.portal import EvaluationsView, SectionEvaluationView

urlpatterns = [
    path("evaluations/", EvaluationsView.as_view(), name="evaluations"),
    path("sections/<int:pk>/evaluation/", SectionEvaluationView.as_view(), name="evaluation_results"),
]
