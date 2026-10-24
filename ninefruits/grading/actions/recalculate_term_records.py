"""Recalculates term records from finalized grades, e.g. after a grading policy change (original
``RecalculateTermRecords``). With a term: students with grades in it, from that term on. Standing
and honors stay as decided at term close."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied

from ninefruits.audit.logger import audit
from ninefruits.grading.services.term_records import TermRecordCalculator
from ninefruits.security.enums import Permission

from ._support import require_reason

CHUNK = 500


class RecalculateTermRecords:
    def __init__(self, calculator: TermRecordCalculator | None = None) -> None:
        self._calculator = calculator

    @property
    def calculator(self) -> TermRecordCalculator:
        if self._calculator is None:
            self._calculator = TermRecordCalculator()
        return self._calculator

    def handle(self, term: Any, only: Any, reason: str, staff: Any) -> int:
        """Returns the number of students recalculated. ``staff`` is ``None`` for a console run."""
        from ninefruits.registration.models import Enrollment

        if staff is not None and not staff.has_perm(Permission.GRADES_MANAGE):
            raise PermissionDenied
        reason = require_reason(reason)
        enrollments = Enrollment.objects.filter(grade_finalized_at__isnull=False)
        if term is not None:
            enrollments = enrollments.filter(
                student_record_id__in=Enrollment.objects.filter(term_id=term.pk).values("student_record_id")
            )
        if only is not None:
            enrollments = enrollments.filter(student_record_id=only.pk)
        record_ids = sorted(set(enrollments.values_list("student_record_id", flat=True)))
        for start in range(0, len(record_ids), CHUNK):
            self.calculator.recalculate_many(record_ids[start : start + CHUNK], term)
        audit(
            "grades.recalculated",
            term if term is not None else only,
            reason=reason,
            properties={
                "term": term.code if term is not None else None,
                "student": only.student_number if only is not None else None,
                "students": len(record_ids),
            },
            causer=staff,
        )
        return len(record_ids)
