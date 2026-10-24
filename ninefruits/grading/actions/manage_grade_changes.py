"""Changing a finalized grade (original ``ManageGradeChanges``, porting-plan 8, 17.2): the
section's instructor or staff with ``grade_changes.request`` ask with a reason; someone else with
``grade_changes.approve`` for the section decides. Approval applies the change in the same
transaction, the only way the database lets a finalized grade change
(``util.guard_finalized_grade`` with ``app.grade_change_request_id``)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.grading.enums import GradeChangeStatus, GradeStatus
from ninefruits.grading.models import GradeChangeRequest
from ninefruits.grading.services.options import GradeOptions
from ninefruits.grading.services.term_records import TermRecordCalculator
from ninefruits.security.enums import Permission

from ._support import now, require_reason

SET_REQUEST = "SELECT set_config('app.grade_change_request_id', %s, true)"


def _score(value: Any) -> str | None:
    return None if value is None else format(value, "f")


class ManageGradeChanges:
    def __init__(self, options: GradeOptions | None = None, records: TermRecordCalculator | None = None) -> None:
        self._options = options
        self._records = records

    @property
    def options(self) -> GradeOptions:
        if self._options is None:
            self._options = GradeOptions()
        return self._options

    @property
    def records(self) -> TermRecordCalculator:
        if self._records is None:
            self._records = TermRecordCalculator()
        return self._records

    def can_request(self, enrollment: Any, user: Any) -> bool:
        section = enrollment.section
        return bool(section.is_taught_by(user) or section.is_in_scope_of(user, Permission.GRADE_CHANGES_REQUEST))

    def request(
        self, enrollment: Any, to_grade: str | None, reason: str, requester: Any, to_score: Any = None
    ) -> GradeChangeRequest:
        """Absolute evaluation: the new score (the grade follows). Relative: the new grade."""
        if not self.can_request(enrollment, requester):
            raise PermissionDenied
        if enrollment.grade_status != GradeStatus.FINALIZED:
            raise ValidationError({"grade": _("Only a final grade needs a change request.")})
        reason = require_reason(reason)
        choice = self.options.resolve(enrollment, to_grade, to_score)
        if choice.item is None:
            raise ValidationError({"to_grade_code": _("Enter the new score or grade.")})
        if choice.item.code == enrollment.grade_code and _score(choice.score) == _score(enrollment.score):
            raise ValidationError({"to_grade_code": _("The new grade is the current grade.")})
        pending_message = _("A change request for this grade is already open.")
        if GradeChangeRequest.objects.filter(enrollment_id=enrollment.pk).pending().exists():
            raise ValidationError({"to_grade_code": pending_message})
        try:
            # A savepoint, so a concurrent duplicate does not abort the caller's transaction.
            with transaction.atomic():
                change = GradeChangeRequest.objects.create(
                    enrollment_id=enrollment.pk,
                    from_grade_code=enrollment.grade_code,
                    to_grade_code=choice.item.code,
                    to_score=choice.score,
                    reason=reason,
                    requested_by_id=requester.pk,
                    requested_at=now(),
                )
        except IntegrityError:
            raise ValidationError({"to_grade_code": pending_message}) from None
        audit(
            "grade_change.requested",
            change,
            reason=reason,
            properties={"from": enrollment.grade_code, "to": choice.item.code, "score": _score(choice.score)},
            causer=requester,
        )
        return change

    def approve(self, change: GradeChangeRequest, approver: Any, note: str | None = None) -> GradeChangeRequest:
        from ninefruits.registration.models import Enrollment

        self._authorize_decision(change, approver)
        note = (note or "").strip() or None
        with transaction.atomic():
            # Only the enrollment is locked and read (the approver may not read the student record).
            enrollment = Enrollment.objects.select_for_update().get(pk=change.enrollment_id)
            choice = self.options.resolve(
                enrollment, change.to_grade_code if change.to_score is None else None, change.to_score
            )
            change.status = GradeChangeStatus.APPROVED
            change.decided_by_id = approver.pk
            change.decided_at = now()
            change.decision_note = note
            change.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])

            # The guard trigger lets the finalized grade change for this approved request only.
            with connection.cursor() as cursor:
                cursor.execute(SET_REQUEST, [str(change.pk)])
            for column, value in choice.attributes().items():
                setattr(enrollment, column, value)
            enrollment.save(
                update_fields=[
                    "grade_scale_id",
                    "grade_code",
                    "score",
                    "grade_points",
                    "counts_in_gpa",
                    "is_passed",
                    "updated_at",
                ]
            )
            with connection.cursor() as cursor:
                cursor.execute(SET_REQUEST, [""])

            change.applied_at = now()
            change.save(update_fields=["applied_at", "updated_at"])
            audit(
                "grade_change.approved",
                change,
                reason=change.reason,
                properties={
                    "enrollment_id": enrollment.pk,
                    "from": change.from_grade_code,
                    "to": change.to_grade_code,
                    "note": note,
                },
                causer=approver,
            )
            from ninefruits.term.models import Term

            self.records.recalculate_many([enrollment.student_record_id], Term.objects.get(pk=enrollment.term_id))
        change.refresh_from_db()
        return change

    def reject(self, change: GradeChangeRequest, approver: Any, note: str) -> GradeChangeRequest:
        self._authorize_decision(change, approver)
        note = require_reason(note, "note")
        change.status = GradeChangeStatus.REJECTED
        change.decided_by_id = approver.pk
        change.decided_at = now()
        change.decision_note = note
        change.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
        audit("grade_change.rejected", change, reason=note, causer=approver)
        return change

    def cancel(self, change: GradeChangeRequest, requester: Any) -> GradeChangeRequest:
        if change.requested_by_id != requester.pk or change.status != GradeChangeStatus.PENDING:
            raise PermissionDenied
        change.status = GradeChangeStatus.CANCELLED
        change.decided_at = now()
        change.save(update_fields=["status", "decided_at", "updated_at"])
        audit("grade_change.cancelled", change, causer=requester)
        return change

    def can_decide(self, change: GradeChangeRequest, user: Any) -> bool:
        return (
            change.status == GradeChangeStatus.PENDING
            and change.requested_by_id != user.pk
            and change.enrollment.section.is_in_scope_of(user, Permission.GRADE_CHANGES_APPROVE)
        )

    def _authorize_decision(self, change: GradeChangeRequest, approver: Any) -> None:
        if change.status != GradeChangeStatus.PENDING:
            raise ValidationError({"status": _("The request is already decided.")})
        # Separation of duties (also a database constraint).
        if change.requested_by_id == approver.pk:
            raise ValidationError({"status": _("You cannot decide your own request.")})
        if not change.enrollment.section.is_in_scope_of(approver, Permission.GRADE_CHANGES_APPROVE):
            raise PermissionDenied
