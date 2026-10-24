"""Certificate enums (original ``App\\Domain\\Certificate\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class CertificateAudience(models.TextChoices):
    """Which student records a certificate kind is for."""

    ANY = "any", _("Any student record")
    ENROLLED = "enrolled", _("Students (not graduated)")
    GRADUATED = "graduated", _("Graduates")


class CertificateIssueStatus(models.TextChoices):
    ISSUED = "issued", pgettext_lazy("certificate.statuses", "Issued")
    REVOKED = "revoked", pgettext_lazy("certificate", "Revoked")


class VerificationReason(models.TextChoices):
    """Why a verification code is not valid (``CertificateVerification.check``); the label is the
    verification page's answer."""

    UNKNOWN = "unknown", _("No certificate matches this code.")
    REVOKED = "revoked", _("This certificate has been revoked.")
    EXPIRED = "expired", _("The verification period for this certificate has ended. Ask the holder for a current one.")
