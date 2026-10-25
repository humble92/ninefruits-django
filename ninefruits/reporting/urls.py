"""Reporting routes outside the admin: the CSV download of a standard report (original
``reports.csv``, ``/reports/{report}.csv``)."""

from __future__ import annotations

from django.urls import path

from .views.csv import ReportCsvView

app_name = "reporting"

urlpatterns = [
    path("reports/<slug:report>.csv", ReportCsvView.as_view(), name="csv"),
]
