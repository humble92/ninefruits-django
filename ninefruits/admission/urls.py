"""Admission routes outside the admin and the portal: the public admissions page, the email
verification notice and application document downloads."""

from __future__ import annotations

from django.urls import path

from .views.public import AdmissionCycleListView, ApplicationDocumentView, VerifyEmailView

app_name = "admission"

urlpatterns = [
    path("admissions/", AdmissionCycleListView.as_view(), name="index"),
    path("admissions/verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    path(
        "applications/<int:pk>/documents/<int:media_id>/",
        ApplicationDocumentView.as_view(),
        name="document",
    ),
]
