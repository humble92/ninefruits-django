"""Grading routes outside the admin and the portal: the staff grade report of a student record
(original ``transcripts.show``)."""

from __future__ import annotations

from django.urls import path

from .views.transcript import StaffTranscriptView

app_name = "grading"

urlpatterns = [
    path("student-records/<int:pk>/transcript/", StaffTranscriptView.as_view(), name="transcript"),
]
