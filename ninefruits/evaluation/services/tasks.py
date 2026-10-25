"""What a student has to evaluate (original ``EvaluationTasks``, legacy counsel/student_list.php):
registered or completed courses of terms with a course evaluation, whose course version requires
one, while the course evaluation window of the section's session is open for the student.
Withdrawn and dropped courses are not evaluated."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ninefruits.evaluation.models import EvaluationCompletion, TermEvaluation
from ninefruits.evaluation.settings import EvaluationSettings
from ninefruits.term.enums import TermWindowType
from ninefruits.term.services import TermResolver


class EvaluationTasks:
    def __init__(self, terms: TermResolver | None = None, settings: EvaluationSettings | None = None) -> None:
        self.terms = terms or TermResolver()
        self._settings = settings

    @property
    def settings(self) -> EvaluationSettings:
        if self._settings is None:
            self._settings = EvaluationSettings.load()
        return self._settings

    def open(self, record: Any, at: datetime | None = None) -> list[Any]:
        """Enrollments the student can evaluate now, done or not, by section label."""
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        enrollments = list(
            Enrollment.objects.filter(
                student_record_id=record.pk,
                status__in=[EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED],
                term_id__in=TermEvaluation.objects.values("term_id"),
                version__requires_evaluation=True,
            ).select_related("section__session", "section__course", "version", "term")
        )
        if not enrollments:
            return []
        # One look at the open windows for all courses (TermResolver::isOpenInSession per course).
        windows = self.terms.open_windows(TermWindowType.COURSE_EVALUATION, at)
        sessions = {window.session_id for window in windows if window.eligibility.matches(record)}
        found = [enrollment for enrollment in enrollments if enrollment.section.session_id in sessions]
        return sorted(found, key=lambda enrollment: enrollment.section.label())

    def done_ids(self, enrollments: list[Any]) -> set[int]:
        return set(
            EvaluationCompletion.objects.filter(enrollment_id__in=[e.pk for e in enrollments]).values_list(
                "enrollment_id", flat=True
            )
        )

    def pending(self, record: Any, at: datetime | None = None) -> list[Any]:
        found = self.open(record, at)
        done = self.done_ids(found)
        return [enrollment for enrollment in found if enrollment.pk not in done]

    def is_open(self, enrollment: Any, at: datetime | None = None) -> bool:
        return any(found.pk == enrollment.pk for found in self.open(enrollment.student_record, at))

    def blocked_term_ids(self, record: Any, at: datetime | None = None) -> list[int]:
        """Terms whose grades stay hidden: the evaluation is open and not finished (setting).
        The block ends with the window, so a missed evaluation does not hide grades for good (the
        legacy lock never ended)."""
        if not self.settings.grades_require_evaluation:
            return []
        return list(dict.fromkeys(enrollment.term_id for enrollment in self.pending(record, at)))
