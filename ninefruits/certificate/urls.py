"""Certificate routes outside the admin and the portal: the public verification page (original
``certificates.verify``, ``/verify/{code?}``) and the PDF download (``certificates.download``)."""

from __future__ import annotations

from django.urls import path

from .views.download import CertificateDownloadView
from .views.public import VerifyCertificateView

app_name = "certificate"

urlpatterns = [
    path("verify/", VerifyCertificateView.as_view(), name="verify_form"),
    path("verify/<str:code>/", VerifyCertificateView.as_view(), name="verify"),
    path("certificates/<int:pk>/download/", CertificateDownloadView.as_view(), name="download"),
]
