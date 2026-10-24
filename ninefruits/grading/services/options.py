"""The grades an enrollment may receive and how an entry becomes a grade (original
``GradeOptions``, decided 2026-10-22, corrected 2026-10-23):

- Absolute evaluation (the default): the score is the source. The grade follows from the score's
  range on the institution's scale. Only grades without a GPA value that apply to every course
  (e.g. I) are chosen directly.
- Relative evaluation: grades only, no score.
- Pass/fail courses: P or NP (or I), no score.

The institution's scale is the default grade scale, fixed at installation. A retake gets at most
the configured cap grade: an absolute grade above it is lowered, a relative one is refused."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from ninefruits.curriculum.enums import GradingBasis
from ninefruits.grading.data import GradeChoice
from ninefruits.grading.enums import EvaluationMethod, GradeAppliesTo
from ninefruits.grading.models import GradeScale, GradeScaleItem
from ninefruits.grading.settings import GradingSettings


def parse_score(value: Any) -> Decimal | None:
    """A score as entered (``"91.5"``) with 2 decimals; empty means none."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    try:
        score = Decimal(str(value).strip())
    except InvalidOperation:
        raise ValidationError(
            {"score": _("The %(attribute)s field must be a number.") % {"attribute": _("Score (%)")}}
        ) from None
    if not score.is_finite():
        raise ValidationError({"score": _("The %(attribute)s field must be a number.") % {"attribute": _("Score (%)")}})
    return score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def score_text(score: Decimal | None) -> str:
    """A stored score for an input field: 91.50 -> "91.5", 97.00 -> "97"."""
    if score is None:
        return ""
    text = format(Decimal(score), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


class GradeOptions:
    def __init__(self, settings: GradingSettings | None = None) -> None:
        self.settings = settings or GradingSettings.load()
        self._scale: GradeScale | None = None
        self._items: list[GradeScaleItem] | None = None

    def scale(self) -> GradeScale:
        if self._scale is None:
            scale = GradeScale.objects.filter(is_default=True).first()
            if scale is None:
                raise ValidationError({"grade_code": _("There is no default grade scale.")})
            self._scale = scale
        return self._scale

    def items(self) -> list[GradeScaleItem]:
        if self._items is None:
            self._items = list(GradeScaleItem.objects.filter(grade_scale=self.scale()).order_by("sort_order", "id"))
        return self._items

    def for_enrollment(self, enrollment: Any) -> list[GradeScaleItem]:
        """Grades to choose from directly for the enrollment (its version and section loaded)."""
        items = self._applicable(enrollment)
        if self.takes_score(enrollment):
            items = [item for item in items if item.applies_to == GradeAppliesTo.BOTH and not item.counts_in_gpa]
        return items

    def codes_for(self, enrollment: Any) -> list[str]:
        return [item.code for item in self.for_enrollment(enrollment)]

    def takes_score(self, enrollment: Any) -> bool:
        """Whether the grade comes from a score: absolute evaluation of a graded course."""
        return (
            enrollment.section.evaluation_method == EvaluationMethod.ABSOLUTE
            and enrollment.version.grading_basis == GradingBasis.GRADED
        )

    def resolve(self, enrollment: Any, code: str | None, score: Any) -> GradeChoice:
        parsed = parse_score(score)
        code = (code or "").strip() or None

        if not self.takes_score(enrollment):
            if parsed is not None:
                raise ValidationError(
                    {
                        "score": _(
                            "This section takes grades only (relative evaluation or a pass/fail course): leave the "
                            "score empty."
                        )
                    }
                )
            return GradeChoice(None if code is None else self._choose(enrollment, code), None)

        # Absolute: a directly chosen grade (e.g. I) without a score, or the score's grade.
        if code is not None and parsed is None:
            return GradeChoice(self._choose(enrollment, code), None)
        if parsed is None:
            return GradeChoice(None, None)

        item = next(
            (
                item
                for item in self._applicable(enrollment)
                if item.min_percentage is not None
                and item.max_percentage is not None
                and Decimal(item.min_percentage) <= parsed <= Decimal(item.max_percentage)
            ),
            None,
        )
        if item is None:
            raise ValidationError({"score": _("No grade covers the score %(score)s.") % {"score": format(parsed, "f")}})
        # A retake above the cap gets the cap grade; the score stays as entered.
        cap = self._cap(enrollment)
        if cap is not None and _points(item) > _points(cap):
            item = cap
        return GradeChoice(item, parsed)

    def _choose(self, enrollment: Any, code: str) -> GradeScaleItem:
        item = next((item for item in self.for_enrollment(enrollment) if item.code == code), None)
        if item is None:
            raise ValidationError(
                {"grade_code": _("The grade %(grade)s is not allowed for this course.") % {"grade": code}}
            )
        cap = self._cap(enrollment)
        if cap is not None and item.grade_points is not None and _points(item) > _points(cap):
            raise ValidationError({"grade_code": _("A retake can receive at most %(grade)s.") % {"grade": cap.code}})
        return item

    def _applicable(self, enrollment: Any) -> list[GradeScaleItem]:
        basis = (
            GradeAppliesTo.PASS_FAIL
            if enrollment.version.grading_basis == GradingBasis.PASS_FAIL
            else GradeAppliesTo.GRADED
        )
        return [item for item in self.items() if item.applies_to in (basis, GradeAppliesTo.BOTH)]

    def _cap(self, enrollment: Any) -> GradeScaleItem | None:
        maximum = self.settings.retake_max_grade
        if not enrollment.is_retake or not maximum:
            return None
        return next((item for item in self.items() if item.code == maximum), None)


def _points(item: GradeScaleItem) -> Decimal:
    return Decimal(item.grade_points) if item.grade_points is not None else Decimal(0)
