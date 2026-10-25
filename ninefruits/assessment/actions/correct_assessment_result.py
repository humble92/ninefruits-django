"""Corrections of published results (original ``CorrectAssessmentResult``, decided 2026-10-23):
staff who record results request with the new values and a reason; someone else with
``assessments.manage`` approves (which applies the values) or rejects with a note. Like grade
changes (ADR 0011): the requester never decides their own request."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

from ninefruits.assessment.enums import CorrectionStatus
from ninefruits.assessment.models import AssessmentResult, AssessmentResultCorrection
from ninefruits.audit.logger import audit
from ninefruits.security.enums import Permission

from ._support import json_value, now, require_reason
from .record_assessment_result import RecordAssessmentResult


def normalize_proposal(proposed: dict[str, Any]) -> dict[str, Any]:
    """``{scores: {code: score}, total, passed, note}`` as stored in ``proposed`` (JSON)."""
    scores = proposed.get("scores") or {}
    return {
        "scores": {str(code): json_value(value) for code, value in dict(scores).items()},
        "total": json_value(proposed.get("total")),
        "passed": proposed.get("passed"),
        "note": proposed.get("note"),
    }


class CorrectAssessmentResult:
    def __init__(self, results: RecordAssessmentResult | None = None) -> None:
        self.results = results or RecordAssessmentResult()

    def request(
        self, result: AssessmentResult, proposed: dict[str, Any], reason: str, staff: Any
    ) -> AssessmentResultCorrection:
        if not staff.has_perm(Permission.ASSESSMENTS_RECORD):
            raise PermissionDenied
        if not result.is_locked():
            raise ValidationError({"result": _("This result is not published; enter it directly.")})
        reason = require_reason(reason)
        proposal = normalize_proposal(proposed)
        pending = _("A correction request is already pending for this result.")
        try:
            # A savepoint, so a concurrent duplicate does not abort the caller's transaction.
            with transaction.atomic():
                correction = AssessmentResultCorrection.objects.create(
                    result_id=result.pk,
                    proposed=proposal,
                    previous=result.values(),
                    reason=reason,
                    requested_by_id=staff.pk,
                    requested_at=now(),
                )
        except IntegrityError:
            raise ValidationError({"result": pending}) from None
        audit(
            "assessment.correction_requested",
            correction,
            reason=reason,
            properties={"result_id": result.pk, "proposed": proposal},
            causer=staff,
        )
        return correction

    def approve(
        self, correction: AssessmentResultCorrection, approver: Any, note: str | None = None
    ) -> AssessmentResultCorrection:
        self._authorize_decision(correction, approver)
        note = (note or "").strip() or None
        result = AssessmentResult.objects.select_related("registration").get(pk=correction.result_id)
        if result.registration is None:
            raise ValidationError({"result": _("This result is not published; enter it directly.")})
        proposed = correction.proposed or {}
        with transaction.atomic():
            self.results.for_registration(
                result.registration,
                dict(proposed.get("scores") or {}),
                proposed.get("passed"),
                approver,
                proposed.get("total"),
                proposed.get("note"),
                applying_correction=True,
            )
            correction.status = CorrectionStatus.APPROVED
            correction.decided_by_id = approver.pk
            correction.decided_at = now()
            correction.decision_note = note
            correction.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
        audit(
            "assessment.correction_approved",
            correction,
            reason=note,
            properties={"result_id": result.pk},
            causer=approver,
        )
        return correction

    def reject(self, correction: AssessmentResultCorrection, approver: Any, note: str) -> AssessmentResultCorrection:
        self._authorize_decision(correction, approver)
        note = require_reason(note, "note")
        correction.status = CorrectionStatus.REJECTED
        correction.decided_by_id = approver.pk
        correction.decided_at = now()
        correction.decision_note = note
        correction.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
        audit(
            "assessment.correction_rejected",
            correction,
            reason=note,
            properties={"result_id": correction.result_id},
            causer=approver,
        )
        return correction

    def cancel(self, correction: AssessmentResultCorrection, requester: Any) -> AssessmentResultCorrection:
        if correction.requested_by_id != requester.pk or correction.status != CorrectionStatus.PENDING:
            raise PermissionDenied
        correction.status = CorrectionStatus.CANCELLED
        correction.decided_at = now()
        correction.save(update_fields=["status", "decided_at", "updated_at"])
        audit("assessment.correction_cancelled", correction, causer=requester)
        return correction

    def can_decide(self, correction: AssessmentResultCorrection, user: Any) -> bool:
        return bool(
            correction.status == CorrectionStatus.PENDING
            and correction.requested_by_id != user.pk
            and user.has_perm(Permission.ASSESSMENTS_MANAGE)
        )

    def _authorize_decision(self, correction: AssessmentResultCorrection, approver: Any) -> None:
        if not approver.has_perm(Permission.ASSESSMENTS_MANAGE):
            raise PermissionDenied
        if correction.status != CorrectionStatus.PENDING:
            raise ValidationError({"status": _("The request is already decided.")})
        if correction.requested_by_id == approver.pk:
            raise ValidationError({"status": _("You cannot decide your own correction request.")})
