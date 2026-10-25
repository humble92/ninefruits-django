"""Staff with ``grades.manage`` for the section finalize its submitted grades (the enrollments
become completed) or return them to the instructors with a reason (original
``FinalizeGrades``). The legacy had no such step: a saved grade was final for the professor and
교무처 edited it directly."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.core.events import dispatch
from ninefruits.grading.enums import GradeStatus
from ninefruits.grading.events import GradesFinalized
from ninefruits.grading.notifications import send_grades_returned
from ninefruits.grading.services.term_records import TermRecordCalculator
from ninefruits.security.enums import Permission

from ._support import now, require_reason


class FinalizeGrades:
    def __init__(self, records: TermRecordCalculator | None = None) -> None:
        self._records = records

    @property
    def records(self) -> TermRecordCalculator:
        if self._records is None:
            self._records = TermRecordCalculator()
        return self._records

    def finalize(self, section: Any, staff: Any) -> int:
        """Returns the number of grades finalized."""
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        self._authorize(section, staff)
        with transaction.atomic():
            open_rows = list(
                Enrollment.objects.select_for_update()
                .filter(section_id=section.pk, status=EnrollmentStatus.ENROLLED)
                .values_list("pk", "student_record_id", "grade_status")
            )
            not_submitted = sum(1 for _pk, _record, status in open_rows if status != GradeStatus.SUBMITTED)
            if not open_rows or not_submitted:
                raise ValidationError(
                    {"grades": _("Not all grades are submitted (%(count)s missing).") % {"count": not_submitted}}
                )
            ids = [pk for pk, _record, _status in open_rows]
            Enrollment.objects.filter(pk__in=ids).update(
                status=EnrollmentStatus.COMPLETED,
                grade_status=GradeStatus.FINALIZED,
                grade_finalized_at=now(),
                grade_finalized_by_id=staff.pk,
            )
            audit("grades.finalized", section, properties={"count": len(ids)}, causer=staff)
            self.records.recalculate_many([record for _pk, record, _status in open_rows], section.term)
            dispatch(GradesFinalized(section, ids))
        return len(ids)

    def return_grades(self, section: Any, staff: Any, reason: str) -> int:
        """Back to the instructors as drafts, e.g. when a grade looks wrong before finalizing."""
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        self._authorize(section, staff)
        reason = require_reason(reason)
        with transaction.atomic():
            count = Enrollment.objects.filter(
                section_id=section.pk, status=EnrollmentStatus.ENROLLED, grade_status=GradeStatus.SUBMITTED
            ).update(grade_status=GradeStatus.DRAFT, grade_submitted_at=None, grade_submitted_by=None)
            if count == 0:
                raise ValidationError({"grades": _("There are no submitted grades.")})
            audit("grades.returned", section, reason=reason, properties={"count": count}, causer=staff)

        from ninefruits.offering.models import SectionInstructor

        for assignment in SectionInstructor.objects.filter(section_id=section.pk).select_related(
            "instructor__person__user"
        ):
            send_grades_returned(getattr(assignment.instructor.person, "user", None), section, reason)
        return count

    def _authorize(self, section: Any, staff: Any) -> None:
        if not section.is_in_scope_of(staff, Permission.GRADES_MANAGE):
            raise PermissionDenied
