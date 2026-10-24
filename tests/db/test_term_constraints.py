"""Original tests/Database/Term/TermConstraintsTest.php."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.utils import timezone

from tests.db.support import database_error
from tests.factories.grading import GradeScaleFactory, GradeScaleItemFactory
from tests.factories.term import AcademicYearFactory, TermFactory, TermTypeFactory, TermWindowFactory, academic_year_for

pytestmark = pytest.mark.django_db


def test_rejects_overlapping_academic_years() -> None:
    academic_year_for(2026)

    error = database_error(
        lambda: AcademicYearFactory(code="X", start_date=date(2027, 1, 1), end_date=date(2027, 12, 31))
    )
    assert "academic_years_no_overlap_excl" in (error or "")


def test_rejects_overlapping_terms_of_the_same_type_but_allows_different_types() -> None:
    year = academic_year_for(2026)
    spring = TermTypeFactory()
    summer = TermTypeFactory()
    TermFactory(
        academic_year=year, term_type=spring, code="2026-SP", start_date=date(2026, 3, 2), end_date=date(2026, 6, 20)
    )

    overlapping = database_error(
        lambda: TermFactory(
            academic_year=academic_year_for(2030),
            term_type=spring,
            code="X",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 7, 1),
        )
    )
    assert "terms_no_overlap_excl" in (overlapping or "")
    assert (
        database_error(
            lambda: TermFactory(
                academic_year=year,
                term_type=summer,
                code="2026-SU",
                start_date=date(2026, 6, 15),
                end_date=date(2026, 7, 31),
            )
        )
        is None
    )


def test_requires_a_window_to_close_after_it_opens() -> None:
    now = timezone.now()
    assert "term_windows_order_check" in (
        database_error(lambda: TermWindowFactory(opens_at=now, closes_at=now - timedelta(hours=1))) or ""
    )


def test_allows_only_one_default_grade_scale() -> None:
    GradeScaleFactory(is_default=True)

    assert "grade_scales_single_default_unique" in (database_error(lambda: GradeScaleFactory(is_default=True)) or "")


def test_requires_grade_points_for_grades_counted_in_the_gpa() -> None:
    assert "grade_scale_items_gpa_points_check" in (
        database_error(lambda: GradeScaleItemFactory(code="X", grade_points=None, counts_in_gpa=True)) or ""
    )
    assert database_error(lambda: GradeScaleItemFactory(code="P", grade_points=None, counts_in_gpa=False)) is None
