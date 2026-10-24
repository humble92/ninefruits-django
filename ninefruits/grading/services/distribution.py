"""Relative evaluation must follow the institution's grade caps (original
``GradeDistributionCheck``, decided 2026-10-23): each grade group (the letter) may take at most
its cap of the section's graded students, plus the tolerance. Small sections are exempt. Grades
without a GPA value (P, NP, I) and withdrawn students are left out of the count."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.utils.translation import gettext as _

from ninefruits.grading.data import GradeDistribution, GroupShare
from ninefruits.grading.enums import EvaluationMethod
from ninefruits.grading.settings import GradingSettings


def _number(value: Decimal) -> str:
    """1 decimal, without a trailing ".0" (PHP prints 40.0 as 40)."""
    text = format(value, "f")
    return text[:-2] if text.endswith(".0") else text


class GradeDistributionCheck:
    def __init__(self, settings: GradingSettings | None = None) -> None:
        self.settings = settings or GradingSettings.load()

    def for_section(self, section: Any, codes: Iterable[str | None] | None = None) -> GradeDistribution:
        """Checks the grades on the section (entered or submitted). Pass unsaved grades to check
        them instead."""
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        if codes is None:
            codes = Enrollment.objects.filter(
                section_id=section.pk, status=EnrollmentStatus.ENROLLED, counts_in_gpa=True
            ).values_list("grade_code", flat=True)
        graded = [code for code in codes if code]
        counts = Counter(code[:1].upper() for code in graded)
        return self.check(len(graded), dict(counts), section.evaluation_method == EvaluationMethod.RELATIVE)

    def check(self, graded: int, counts_by_group: dict[str, int], relative: bool = True) -> GradeDistribution:
        minimum = int(self.settings.relative_minimum_students)
        caps = {str(group).upper(): int(cap) for group, cap in (self.settings.relative_grade_caps or {}).items()}
        tolerance = int(self.settings.relative_cap_tolerance_percent)
        checked = relative and graded >= minimum and graded > 0
        groups: dict[str, GroupShare] = {}
        violations: list[str] = []
        for group in sorted(dict.fromkeys([*caps, *counts_by_group])):
            count = int(counts_by_group.get(group, 0))
            cap = caps.get(group)
            percent = (
                Decimal(0)
                if graded == 0
                else (Decimal(count * 100) / Decimal(graded)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
            )
            limit = None if cap is None else cap + tolerance
            over = checked and limit is not None and percent > limit
            groups[group] = GroupShare(count=count, percent=percent, cap=cap, limit=limit, over=over)
            if over:
                violations.append(
                    _("%(group)s: %(percent)s%% of the students, cap %(cap)s%% (up to %(limit)s%% allowed)")
                    % {"group": group, "percent": _number(percent), "cap": cap, "limit": limit}
                )
        return GradeDistribution(graded, minimum, checked, groups, violations)
