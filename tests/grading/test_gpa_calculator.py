"""GPA calculation (original ``tests/Feature/Grading/GpaCalculatorTest.php``): rounding and
cutting at the configured decimals with exact boundaries, attempted/earned/GPA credits, retakes in
the cumulative GPA by policy. Integer arithmetic: no float error."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ninefruits.grading.data import GradedCourse
from ninefruits.grading.services import GpaCalculator

from .conftest import grading_settings


def calculator(decimals: int = 2, rounding: str = "round", retakes: str = "latest") -> GpaCalculator:
    return GpaCalculator(grading_settings(gpa_decimals=decimals, gpa_rounding=rounding, retake_policy=retakes))


def course(
    enrollment_id: int,
    credits: float,
    points: float | None,
    passed: bool = True,
    repeats: int | None = None,
    term_start: str = "2026-03-02",
    counts_in_gpa: bool | None = None,
) -> GradedCourse:
    """``points`` ``None`` for P/NP/I."""
    return GradedCourse(
        enrollment_id=enrollment_id,
        term_id=1,
        term_start=term_start,
        credit_tenths=round(credits * 10),
        point_hundredths=None if points is None else round(points * 100),
        counts_in_gpa=counts_in_gpa if counts_in_gpa is not None else points is not None,
        is_passed=passed,
        repeats_enrollment_id=repeats,
    )


def text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


EIGHT_CREDITS = [course(1, 3, 4.0), course(2, 3, 3.5), course(3, 2, 2.5)]  # 27.5 / 8 = 3.4375


@pytest.mark.parametrize(
    ("decimals", "rounding", "courses", "expected"),
    [
        pytest.param(2, "round", EIGHT_CREDITS, "3.44", id="two decimals, round"),
        pytest.param(2, "floor", EIGHT_CREDITS, "3.43", id="two decimals, floor"),
        pytest.param(3, "round", EIGHT_CREDITS, "3.438", id="three decimals, exact half"),
        # 4.3 × 1 + 1.7 × 1 = 6.0 over 2 = 3.000: no float error at the boundary
        pytest.param(3, "round", [course(1, 1, 4.3), course(2, 1, 1.7)], "3.000", id="legacy 4.3 points"),
        # 4.0 + 2 × 3.5 = 11 over 3 credits = 3.666…
        pytest.param(2, "floor", [course(1, 1, 4.0), course(2, 2, 3.5)], "3.66", id="repeating decimal floor"),
        pytest.param(2, "round", [course(1, 1, 4.0), course(2, 2, 3.5)], "3.67", id="repeating decimal round"),
        pytest.param(0, "round", [course(1, 3, 4.5), course(2, 3, 3.5)], "4", id="zero decimals"),
        pytest.param(2, "round", [course(1, 3, 4.5), course(2, 3, 0.0, passed=False)], "2.25", id="F counts"),
        pytest.param(2, "round", [course(1, 2, None), course(2, 1, None, passed=False)], None, id="only P/F"),
        pytest.param(2, "round", [], None, id="nothing"),
        pytest.param(2, "round", [course(1, 0.5, 4.5), course(2, 1.5, 3.0)], "3.38", id="half credits"),
    ],
)
def test_rounds_half_up_and_cuts_at_the_configured_decimals(
    decimals: int, rounding: str, courses: list[GradedCourse], expected: str | None
) -> None:
    assert text(calculator(decimals, rounding).totals(courses).gpa) == expected


def test_counts_credits_as_attempted_earned_and_graded() -> None:
    totals = calculator().totals(
        [
            course(1, 3, 4.0),  # A0
            course(2, 3, 0.0, passed=False),  # F: attempted, GPA, not earned
            course(3, 2, None),  # P: attempted, earned, not GPA
            course(4, 1, None, passed=False),  # NP or I: attempted only
        ]
    )
    assert str(totals.attempted_credits) == "9.0"
    assert str(totals.earned_credits) == "5.0"
    assert str(totals.gpa_credits) == "6.0"
    assert str(totals.grade_points_total) == "12.00"
    assert str(totals.gpa) == "2.00"


def test_counts_only_the_latest_attempt_of_a_retaken_course_in_the_cumulative_gpa() -> None:
    courses = [
        course(1, 3, 1.0, term_start="2025-03-02"),  # D0
        course(2, 3, 0.0, passed=False, repeats=1, term_start="2025-09-01"),  # F on the retake
        course(3, 3, 4.0, repeats=2, term_start="2026-03-02"),  # A0 on the second retake
        course(4, 3, 3.0, term_start="2025-03-02"),
    ]
    calc = calculator()
    assert calc.superseded(courses) == {1, 2}
    cumulative = calc.cumulative(courses)
    assert str(cumulative.attempted_credits) == "6.0"
    assert str(cumulative.gpa) == "3.50"


def test_keeps_the_latest_attempt_even_when_it_is_worse_or_the_best_one_by_policy() -> None:
    courses = [course(1, 3, 4.0, term_start="2025-03-02"), course(2, 3, 2.0, repeats=1, term_start="2026-03-02")]
    assert str(calculator().cumulative(courses).gpa) == "2.00"
    assert str(calculator(retakes="best").cumulative(courses).gpa) == "4.00"


def test_keeps_a_term_gpa_with_every_grade_of_the_term() -> None:
    # The retaken attempt still counts in its own term's GPA.
    earlier = [course(1, 3, 1.0, term_start="2025-03-02"), course(4, 3, 3.0, term_start="2025-03-02")]
    assert str(calculator().totals(earlier).gpa) == "2.00"


def test_best_policy_keeps_the_latest_attempt_when_none_counts_in_the_gpa() -> None:
    courses = [course(1, 3, None, term_start="2025-03-02"), course(2, 3, None, repeats=1, term_start="2026-03-02")]
    assert calculator(retakes="best").superseded(courses) == {1}
