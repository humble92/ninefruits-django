"""Curriculum enums (original ``App\\Domain\\Curriculum\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class GradingBasis(models.TextChoices):
    GRADED = "graded", _("Letter grade")
    PASS_FAIL = "pass_fail", pgettext_lazy("curriculum", "Pass/fail")


class ProgramRole(models.TextChoices):
    """How a student follows a program: as the primary program of the record, or as a second
    major or minor. Requirements differ per role."""

    PRIMARY = "primary", pgettext_lazy("curriculum", "Primary program")
    SECOND_MAJOR = "second_major", _("Second major")
    MINOR = "minor", _("Minor")

    @classmethod
    def from_additional(cls, role: str) -> ProgramRole:
        """The role of an additional program (second major or minor)."""
        return cls(str(getattr(role, "value", role)))


class RequirementKind(models.TextChoices):
    #: Minimum credits in a course category (and its subcategories).
    CATEGORY_CREDITS = "category_credits", _("Credits in a category")
    #: Every listed course.
    REQUIRED_COURSES = "required_courses", _("Required courses")
    #: Minimum credits or courses from the listed courses.
    COURSE_GROUP = "course_group", _("Choice from courses")
    #: A passing result for an examination kind (language, comprehensive, thesis).
    ASSESSMENT_PASS = "assessment_pass", _("Passed examination")


class RequisiteKind(models.TextChoices):
    """Prerequisite: completed before (or with ``allows_concurrent``, in the same term).
    Corequisite: taken in the same term unless already completed."""

    PREREQUISITE = "prerequisite", _("Prerequisite")
    COREQUISITE = "corequisite", _("Corequisite")
