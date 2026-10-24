"""Attendance downloads outside the admin and the portal (original ``sections.roster.csv`` and
``sections.attendance.sheet``)."""

from __future__ import annotations

from django.urls import path

from .views.downloads import AttendanceSheetView, RosterCsvView

app_name = "attendance"

urlpatterns = [
    path("sections/<int:pk>/roster.csv", RosterCsvView.as_view(), name="roster_csv"),
    path("sections/<int:pk>/attendance-sheet", AttendanceSheetView.as_view(), name="sheet"),
]
