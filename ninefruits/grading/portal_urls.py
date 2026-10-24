"""Portal routes of the grading, included in ``ninefruits.portal.urls`` (names ``portal:...``)."""

from __future__ import annotations

from django.urls import path

from ninefruits.grading.views.portal import GradeEntryView, MyGradesView
from ninefruits.grading.views.transcript import OwnTranscriptView

urlpatterns = [
    path("sections/<int:pk>/grades/", GradeEntryView.as_view(), name="grade_entry"),
    path("grades/", MyGradesView.as_view(), name="grades"),
    path("grades/transcript/", OwnTranscriptView.as_view(), name="grades_transcript"),
]
