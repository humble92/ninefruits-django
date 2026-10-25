"""Value objects of the grading (original ``App\\Domain\\Grading\\Data``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class CreditTotals:
    """Credits and GPA of a set of graded courses, with the decimals they are stored with."""

    attempted_credits: Decimal
    earned_credits: Decimal
    gpa_credits: Decimal
    grade_points_total: Decimal
    #: ``None`` without GPA credits (only P/F or incomplete courses).
    gpa: Decimal | None


@dataclass(frozen=True)
class GradedCourse:
    """A completed (finalized) enrollment as the GPA calculation sees it. Credits are kept in
    tenths and grade points in hundredths so sums are exact."""

    enrollment_id: int
    term_id: int
    #: Orders attempts: term start date (ISO), then enrollment id.
    term_start: str
    credit_tenths: int
    point_hundredths: int | None
    counts_in_gpa: bool
    is_passed: bool
    repeats_enrollment_id: int | None = None

    @classmethod
    def from_enrollment(cls, enrollment: Any, term_start: Any = None) -> GradedCourse:
        """``term_start`` defaults to the enrollment's term (loaded)."""
        start = term_start if term_start is not None else enrollment.term.start_date
        return cls(
            enrollment_id=int(enrollment.pk),
            term_id=int(enrollment.term_id),
            term_start=start.isoformat() if hasattr(start, "isoformat") else str(start),
            credit_tenths=int((Decimal(enrollment.credits) * 10).to_integral_value()),
            point_hundredths=(
                None
                if enrollment.grade_points is None
                else int((Decimal(enrollment.grade_points) * 100).to_integral_value())
            ),
            counts_in_gpa=bool(enrollment.counts_in_gpa),
            is_passed=bool(enrollment.is_passed),
            repeats_enrollment_id=enrollment.repeats_enrollment_id,
        )


@dataclass(frozen=True)
class GradeChoice:
    """A grade as entered: the grade on the institution's scale and, for absolute evaluation, the
    score it came from."""

    item: Any  # GradeScaleItem | None
    score: Decimal | None

    def is_empty(self) -> bool:
        return self.item is None and self.score is None

    def attributes(self) -> dict[str, Any]:
        """The enrollment columns for this grade."""
        item = self.item
        return {
            "grade_scale_id": item.grade_scale_id if item is not None else None,
            "grade_code": item.code if item is not None else None,
            "score": self.score,
            "grade_points": item.grade_points if item is not None else None,
            "counts_in_gpa": item.counts_in_gpa if item is not None else None,
            "is_passed": item.is_passing if item is not None else None,
        }


@dataclass(frozen=True)
class GroupShare:
    """One grade group (the letter) of a relatively evaluated section against its cap."""

    count: int
    percent: Decimal
    cap: int | None
    limit: int | None
    over: bool

    @property
    def tolerance(self) -> int | None:
        return None if self.cap is None or self.limit is None else self.limit - self.cap


@dataclass(frozen=True)
class GradeDistribution:
    """How a relatively evaluated section's grades spread over the grade groups, against the
    institution's caps."""

    graded: int
    minimum_students: int
    checked: bool
    #: by group letter, sorted
    groups: dict[str, GroupShare]
    #: messages for groups over their cap
    violations: list[str] = field(default_factory=list)

    def passes(self) -> bool:
        return not self.violations

    def as_dict(self) -> dict[str, Any]:
        """For the audit trail."""
        return {
            group: {
                "count": share.count,
                "percent": float(share.percent),
                "cap": share.cap,
                "limit": share.limit,
                "over": share.over,
            }
            for group, share in self.groups.items()
        }


@dataclass(frozen=True)
class OpenSection:
    section: Any
    unfinished_count: int


@dataclass(frozen=True)
class TermClosePreflight:
    """What stands between a term and its close: sections with registered students whose grades
    are not finalized yet."""

    term: Any
    open_sections: list[OpenSection]
    students: int

    def is_ready(self) -> bool:
        return not self.open_sections
