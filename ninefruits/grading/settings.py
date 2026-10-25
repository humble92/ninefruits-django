"""Grading policy (settings group ``grading``, original
``App\\Domain\\Grading\\Settings\\GradingSettings``): GPA precision, retakes, grade caps of relative
evaluation, academic standing and honors. Values come from the data migrations
``appsettings.0010_p6_grading_settings`` and ``0011_p6_relative_grade_caps``."""

from __future__ import annotations

from decimal import Decimal
from typing import ClassVar

from ninefruits.grading.enums import GpaRounding, RetakePolicy
from ninefruits.settings.groups.base import SettingsGroup


class GradingSettings(SettingsGroup):
    group: ClassVar[str] = "grading"

    #: Decimals of term and cumulative GPA (legacy YUST: 3).
    gpa_decimals: int
    gpa_rounding: str
    retake_policy: str
    #: Highest grade a retake may receive (e.g. A0), or ``None`` for no cap.
    retake_max_grade: str | None
    #: Relative evaluation: the most a grade group (the letter: A for A+, A0, A-) may take of a
    #: section's graded students, in percent, e.g. ``{"A": 30, "B": 40}``.
    relative_grade_caps: dict[str, int]
    #: Percent points a group may exceed its cap by.
    relative_cap_tolerance_percent: int
    #: Sections with fewer graded students are not checked against the caps.
    relative_minimum_students: int
    #: Judge warnings and count them only in regular terms (not summer or winter).
    standing_regular_terms_only: bool
    #: A term GPA below this is an academic warning (legacy YUST: 1.3).
    warning_gpa_below: float
    #: Warnings that flag a student for dismissal review; 0 turns it off (legacy YUST: 4).
    dismissal_warning_count: int
    #: Count only consecutive warnings (the legacy counted all).
    dismissal_consecutive_only: bool
    honors_min_gpa: float
    #: GPA credits in the term a student needs for honors.
    honors_min_credits: float
    #: No honors with a failed course in the term.
    honors_exclude_failing: bool

    def rounding(self) -> GpaRounding:
        return GpaRounding(self.gpa_rounding)

    def retakes(self) -> RetakePolicy:
        return RetakePolicy(self.retake_policy)

    @staticmethod
    def decimal(value: float | int) -> Decimal:
        """A float setting as an exact decimal (1.75 -> Decimal("1.75"))."""
        return Decimal(str(value))
