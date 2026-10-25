"""What a student has taken, with equivalent courses counted (original ``CourseHistory``;
porting-plan 10.4: substitutions valid at the time)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django.db.models import Q
from django.utils import timezone

from ninefruits.registration.enums import EnrollmentStatus


class CourseHistory:
    def __init__(self) -> None:
        self._grade_points: dict[str, Decimal | None] = {}

    def accepted_course_ids(self, course_id: int, on: date | None = None) -> list[int]:
        """The course and the courses that count for it on the date."""
        from ninefruits.curriculum.models import CourseEquivalency

        ids = [course_id]
        equivalencies = CourseEquivalency.objects.effective_on(on or timezone.localdate()).filter(
            Q(course_id=course_id) | Q(equivalent_course_id=course_id, is_mutual=True)
        )
        for equivalency in equivalencies:
            other = equivalency.equivalent_course_id if equivalency.course_id == course_id else equivalency.course_id
            if other not in ids:
                ids.append(other)
        return ids

    def has_passed(self, record: Any, course_ids: list[int], minimum_grade: str | None = None) -> bool:
        """Completed and passed enrollments of the person (any of their student records) in the
        courses, at or above a minimum grade on the default scale."""
        from ninefruits.registration.models import Enrollment

        grades = Enrollment.objects.filter(
            student_record__person_id=record.person_id,
            course_id__in=course_ids,
            status=EnrollmentStatus.COMPLETED,
            is_passed=True,
        ).values_list("grade_code", flat=True)
        return any(minimum_grade is None or self.meets_minimum(grade, minimum_grade) for grade in grades)

    def earlier_attempts(self, record: Any, course_ids: list[int], except_term_id: int) -> list[Any]:
        """Earlier enrollments of this record in the courses that count as taking it
        (completed), newest first."""
        from ninefruits.registration.models import Enrollment

        return list(
            Enrollment.objects.filter(
                student_record_id=record.pk, course_id__in=course_ids, status=EnrollmentStatus.COMPLETED
            )
            .exclude(term_id=except_term_id)
            .order_by("-enrolled_at", "-id")
        )

    def meets_minimum(self, grade_code: str | None, minimum_grade: str) -> bool:
        points = self._points(grade_code)
        minimum = self._points(minimum_grade)
        # Without points on the scale (e.g. P/F) a pass is enough.
        return points is None or minimum is None or points >= minimum

    def _points(self, grade_code: str | None) -> Decimal | None:
        if grade_code is None:
            return None
        if grade_code not in self._grade_points:
            from ninefruits.grading.models import GradeScaleItem

            item = GradeScaleItem.objects.filter(grade_scale__is_default=True, code=grade_code).first()
            self._grade_points[grade_code] = None if item is None or item.grade_points is None else item.grade_points
        return self._grade_points[grade_code]
