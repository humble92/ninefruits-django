"""Examination routes outside the admin and the portal: the evidence download."""

from __future__ import annotations

from django.urls import path

from .views.evidence import EvidenceDownloadView

app_name = "assessment"

urlpatterns = [
    path("assessment-results/<int:pk>/evidence/", EvidenceDownloadView.as_view(), name="evidence"),
]
