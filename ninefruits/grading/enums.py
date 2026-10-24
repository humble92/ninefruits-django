"""Grading enums (original ``App\\Domain\\Grading\\Enums``) used by the reference data screens."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


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


class AcademicStanding(models.TextChoices):
    """Standing decided at term close (legacy academic warning reports). Dismissal is only
    flagged for review; the status change itself is a student status change with its own
    approval."""

    GOOD = "good", _("Good standing")
    WARNING = "warning", _("Academic warning")
    DISMISSAL_REVIEW = "dismissal_review", _("Dismissal review")
