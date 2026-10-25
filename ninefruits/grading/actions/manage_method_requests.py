"""Evaluation method requests (original ``ManageEvaluationMethodRequests``). Sections are
evaluated absolutely unless the instructor asks for relative evaluation (decided 2026-10-23). The
instructor requests with a reason before any grade is submitted; the staff who schedule the
section approve or reject with a note, and the instructor is told by email. Approval clears draft
grades, since they were entered under the other method."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.grading.enums import EvaluationMethod, GradeStatus, RequestStatus
from ninefruits.grading.models import EvaluationMethodRequest
from ninefruits.grading.notifications import send_method_decided

from ._support import now, require_reason


class ManageEvaluationMethodRequests:
    def request(
        self, section: Any, method: EvaluationMethod | str, reason: str, instructor: Any
    ) -> EvaluationMethodRequest:
        if not section.is_taught_by(instructor):
            raise PermissionDenied
        method = EvaluationMethod(method)
        if method == section.evaluation_method:
            raise ValidationError({"requested_method": _("The section already uses that evaluation method.")})
        reason = require_reason(reason)
        self.ensure_changeable(section)
        pending = _("A change request for this section is already waiting.")
        if EvaluationMethodRequest.objects.filter(section_id=section.pk).pending().exists():
            raise ValidationError({"requested_method": pending})
        try:
            with transaction.atomic():
                request = EvaluationMethodRequest.objects.create(
                    section_id=section.pk,
                    requested_method=method,
                    reason=reason,
                    requested_by_id=instructor.pk,
                    requested_at=now(),
                )
        except IntegrityError:
            raise ValidationError({"requested_method": pending}) from None
        audit(
            "evaluation_method.requested",
            request,
            reason=reason,
            properties={"section_id": section.pk, "method": method.value},
            causer=instructor,
        )
        return request

    def approve(self, request: EvaluationMethodRequest, staff: Any, note: str | None = None) -> int:
        """Approval changes the section's method and drops draft grades entered under the old
        one. Returns the number of drafts cleared."""
        from ninefruits.registration.enums import EnrollmentStatus
        from ninefruits.registration.models import Enrollment

        self._authorize_decision(request, staff)
        section = request.section
        self.ensure_changeable(section)
        note = (note or "").strip() or None
        with transaction.atomic():
            cleared = Enrollment.objects.filter(
                section_id=section.pk, status=EnrollmentStatus.ENROLLED, grade_status=GradeStatus.DRAFT
            ).update(
                grade_status=GradeStatus.NONE,
                grade_scale=None,
                grade_code=None,
                score=None,
                grade_points=None,
                counts_in_gpa=None,
                is_passed=None,
                grade_entered_at=None,
                grade_entered_by=None,
            )
            section.evaluation_method = request.requested_method
            section.save(update_fields=["evaluation_method", "updated_at"])
            request.status = RequestStatus.APPROVED
            request.decided_by_id = staff.pk
            request.decided_at = now()
            request.decision_note = note
            request.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
            audit(
                "evaluation_method.approved",
                request,
                reason=note,
                properties={"section_id": section.pk, "method": request.requested_method, "drafts_cleared": cleared},
                causer=staff,
            )
        send_method_decided(request, cleared)
        return cleared

    def reject(self, request: EvaluationMethodRequest, staff: Any, note: str) -> EvaluationMethodRequest:
        self._authorize_decision(request, staff)
        note = require_reason(note, "note")
        request.status = RequestStatus.REJECTED
        request.decided_by_id = staff.pk
        request.decided_at = now()
        request.decision_note = note
        request.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
        audit(
            "evaluation_method.rejected",
            request,
            reason=note,
            properties={"section_id": request.section_id},
            causer=staff,
        )
        send_method_decided(request, 0)
        return request

    def cancel(self, request: EvaluationMethodRequest, instructor: Any) -> EvaluationMethodRequest:
        if request.requested_by_id != instructor.pk or request.status != RequestStatus.PENDING:
            raise PermissionDenied
        request.status = RequestStatus.CANCELLED
        request.decided_at = now()
        request.save(update_fields=["status", "decided_at", "updated_at"])
        audit("evaluation_method.cancelled", request, causer=instructor)
        return request

    def can_decide(self, request: EvaluationMethodRequest, user: Any) -> bool:
        return request.status == RequestStatus.PENDING and request.section.is_manageable_by(user)

    def ensure_changeable(self, section: Any) -> None:
        """Not after a grade is submitted or finalized under the current method."""
        from ninefruits.registration.models import Enrollment

        if Enrollment.objects.filter(
            section_id=section.pk, grade_status__in=[GradeStatus.SUBMITTED, GradeStatus.FINALIZED]
        ).exists():
            raise ValidationError(
                {"requested_method": _("Grades are already entered; the evaluation method cannot change.")}
            )

    def _authorize_decision(self, request: EvaluationMethodRequest, staff: Any) -> None:
        if request.status != RequestStatus.PENDING:
            raise ValidationError({"status": _("The request is already decided.")})
        if not request.section.is_manageable_by(staff):
            raise PermissionDenied
