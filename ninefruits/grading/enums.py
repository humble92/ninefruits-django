"""Grading enums (original ``App\\Domain\\Grading\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class GradeAppliesTo(models.TextChoices):
    """Which courses a grade on a scale is for (course version grading basis)."""

    GRADED = "graded", _("Graded courses")
    PASS_FAIL = "pass_fail", _("Pass/fail courses")
    BOTH = "both", _("Both")


class EvaluationMethod(models.TextChoices):
    """How a section is graded (``sections.evaluation_method``). Absolute: instructors enter
    scores and the grades follow. Relative: instructors give grades within the grade caps."""

    ABSOLUTE = "absolute", _("Absolute evaluation")
    RELATIVE = "relative", _("Relative evaluation")

    def other(self) -> EvaluationMethod:
        return EvaluationMethod.RELATIVE if self == EvaluationMethod.ABSOLUTE else EvaluationMethod.ABSOLUTE


class AcademicStanding(models.TextChoices):
    """Standing decided at term close (legacy academic warning reports). Dismissal is only
    flagged for review; the status change itself is a student status change with its own
    approval."""

    GOOD = "good", _("Good standing")
    WARNING = "warning", _("Academic warning")
    DISMISSAL_REVIEW = "dismissal_review", _("Dismissal review")

    def is_warning(self) -> bool:
        return self in (AcademicStanding.WARNING, AcademicStanding.DISMISSAL_REVIEW)


class GradeStatus(models.TextChoices):
    """Grade entry state of an enrollment: none, draft, submitted, finalized. A finalized grade
    changes only through an approved grade change request (``util.guard_finalized_grade``)."""

    NONE = "none", _("No grade")
    DRAFT = "draft", pgettext_lazy("registration", "Draft")
    SUBMITTED = "submitted", pgettext_lazy("registration.grade_statuses", "Submitted")
    FINALIZED = "finalized", pgettext_lazy("registration", "Final")


class GpaRounding(models.TextChoices):
    ROUND = "round", _("Round half up")
    FLOOR = "floor", _("Cut off")


class RetakePolicy(models.TextChoices):
    """Which attempt of a retaken course counts in the cumulative GPA. Term GPAs always keep
    every grade of their term."""

    LATEST = "latest", _("Latest attempt")
    BEST = "best", _("Best attempt")


class GradeChangeStatus(models.TextChoices):
    PENDING = "pending", pgettext_lazy("grading", "Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    CANCELLED = "cancelled", pgettext_lazy("grading", "Cancelled")


class RequestStatus(models.TextChoices):
    """State of a request someone else decides (evaluation method change). Same labels as the
    grade change statuses (original ``grading.change_statuses``)."""

    PENDING = "pending", pgettext_lazy("grading", "Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    CANCELLED = "cancelled", pgettext_lazy("grading", "Cancelled")
