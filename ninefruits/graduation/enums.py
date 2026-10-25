"""Graduation enums (original ``App\\Domain\\Graduation\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class WaiverStatus(models.TextChoices):
    """A waiver counts only while approved. Lifted keeps the history of a waiver taken back."""

    PENDING = "pending", pgettext_lazy("graduation", "Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    LIFTED = "lifted", _("Lifted")
