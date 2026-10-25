"""Examination enums (original ``App\\Domain\\Assessment\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class AssessmentCategory(models.TextChoices):
    """Groups kinds for display and filters; the category does not change behaviour."""

    LANGUAGE = "language", pgettext_lazy("assessment", "Language")
    COMPREHENSIVE = "comprehensive", _("Comprehensive")
    THESIS = "thesis", _("Thesis")
    EXTERNAL = "external", _("External test")


class ScoringMethod(models.TextChoices):
    """Score: the total of the areas against the pass score (and area minimums). Pass/fail:
    staff decide."""

    SCORE = "score", _("Score")
    PASS_FAIL = "pass_fail", pgettext_lazy("assessment", "Pass/fail")


class AssessmentRegistrationStatus(models.TextChoices):
    REGISTERED = "registered", pgettext_lazy("assessment.registration_statuses", "Registered")
    CANCELLED = "cancelled", pgettext_lazy("assessment", "Cancelled")
    ABSENT = "absent", pgettext_lazy("assessment", "Absent")

    @classmethod
    def active(cls) -> tuple[str, ...]:
        """Registrations that hold a seat (original ``scopeActive``)."""
        return (cls.REGISTERED.value, cls.ABSENT.value)


class CorrectionStatus(models.TextChoices):
    PENDING = "pending", pgettext_lazy("assessment", "Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    CANCELLED = "cancelled", pgettext_lazy("assessment", "Cancelled")


class ResultSource(models.TextChoices):
    """Session: sat at one of ours. External: an outside body, recorded with evidence."""

    SESSION = "session", pgettext_lazy("assessment", "Session")
    EXTERNAL = "external", _("External")
