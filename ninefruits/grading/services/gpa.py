"""Term and cumulative GPA (original ``GpaCalculator``; legacy SV_AVR_PRIPNT, SV_AVR_POINT views,
ADR 0011).

- Attempted: every graded course. Earned: passed courses. GPA credits: courses whose grade
  counts in the GPA (F counts with 0 points; P, NP and I do not).
- GPA = sum(points × credits) / GPA credits, to the configured decimals, rounded half up or cut.
  Integer arithmetic, so 3.0045 rounds to 3.005 and never to 3.004.
- Cumulative: of the attempts of a retaken course (linked by ``repeats_enrollment_id``), only one
  counts by the retake policy; the others leave the cumulative totals entirely."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from ninefruits.grading.data import CreditTotals, GradedCourse
from ninefruits.grading.enums import GpaRounding, RetakePolicy
from ninefruits.grading.settings import GradingSettings


def _decimal(scaled: int, decimals: int) -> Decimal:
    """An integer of ``10**-decimals`` units as a Decimal with exactly that many decimals."""
    return Decimal(scaled).scaleb(-decimals)


class GpaCalculator:
    def __init__(self, settings: GradingSettings | None = None) -> None:
        self.settings = settings or GradingSettings.load()

    def totals(self, courses: Iterable[GradedCourse]) -> CreditTotals:
        attempted = earned = gpa_credits = points = 0
        for course in courses:
            attempted += course.credit_tenths
            earned += course.credit_tenths if course.is_passed else 0
            if course.counts_in_gpa and course.point_hundredths is not None:
                gpa_credits += course.credit_tenths
                points += course.point_hundredths * course.credit_tenths
        return CreditTotals(
            attempted_credits=_decimal(attempted, 1),
            earned_credits=_decimal(earned, 1),
            gpa_credits=_decimal(gpa_credits, 1),
            grade_points_total=_decimal(points // 10, 2),
            gpa=self._gpa(points, gpa_credits),
        )

    def cumulative(self, courses: list[GradedCourse]) -> CreditTotals:
        """Totals over all the courses with retakes resolved."""
        superseded = self.superseded(courses)
        return self.totals(course for course in courses if course.enrollment_id not in superseded)

    def superseded(self, courses: list[GradedCourse]) -> set[int]:
        """Enrollment ids that do not count in the cumulative totals because another attempt of
        the same course counts instead."""
        by_id = {course.enrollment_id: course for course in courses}
        root: dict[int, int] = {}

        def find(enrollment_id: int) -> int:
            parent = root.get(enrollment_id, enrollment_id)
            if parent == enrollment_id:
                return enrollment_id
            root[enrollment_id] = find(parent)
            return root[enrollment_id]

        # Group attempts that are linked, directly or through each other.
        for enrollment_id, course in by_id.items():
            if course.repeats_enrollment_id is not None and course.repeats_enrollment_id in by_id:
                root[find(enrollment_id)] = find(course.repeats_enrollment_id)

        groups: dict[int, list[GradedCourse]] = {}
        for enrollment_id, course in by_id.items():
            groups.setdefault(find(enrollment_id), []).append(course)

        superseded: set[int] = set()
        for attempts in groups.values():
            if len(attempts) < 2:
                continue
            kept = self._kept(attempts)
            superseded.update(a.enrollment_id for a in attempts if a.enrollment_id != kept.enrollment_id)
        return superseded

    def _kept(self, attempts: list[GradedCourse]) -> GradedCourse:
        ordered = sorted(attempts, key=lambda a: (a.term_start, a.enrollment_id), reverse=True)
        if self.settings.retakes() == RetakePolicy.LATEST:
            return ordered[0]
        # Best: the highest grade that counts in the GPA, the latest on a tie; the latest
        # attempt when none counts (e.g. all P/F).
        graded = [a for a in ordered if a.counts_in_gpa and a.point_hundredths is not None]
        if not graded:
            return ordered[0]
        best = graded[0]
        for attempt in graded:
            if (attempt.point_hundredths or 0) > (best.point_hundredths or 0):
                best = attempt
        return best

    def _gpa(self, point_credit_thousandths: int, credit_tenths: int) -> Decimal | None:
        """``point_credit_thousandths``: sum of points (hundredths) × credits (tenths)."""
        if credit_tenths == 0:
            return None
        decimals = max(0, min(3, int(self.settings.gpa_decimals)))
        numerator = point_credit_thousandths * 10**decimals
        denominator = credit_tenths * 100
        if self.settings.rounding() == GpaRounding.ROUND:
            scaled = (2 * numerator + denominator) // (2 * denominator)
        else:
            scaled = numerator // denominator
        return _decimal(scaled, decimals)
