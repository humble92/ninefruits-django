"""Waiving one requirement for one student (original ``WaiveRequirement``, decided 2026-10-23:
two people). Staff with ``graduation.process`` request it with a reason; someone else with the
same permission approves or rejects; an approved waiver can be lifted later with a reason.
Every step is audited and the row keeps the history."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.graduation.enums import WaiverStatus
from ninefruits.graduation.models import DegreeRequirementWaiver
from ninefruits.person.models import StudentRecord
from ninefruits.security.enums import Permission

from ._support import authorize, now, require_reason


class WaiveRequirement:
    def request(self, record: StudentRecord, requirement: Any, reason: str, staff: Any) -> DegreeRequirementWaiver:
        authorize(staff, record, Permission.GRADUATION_PROCESS)
        reason = require_reason(reason)
        try:
            # A savepoint, so a duplicate does not abort the caller's transaction.
            with transaction.atomic():
                waiver = DegreeRequirementWaiver.objects.create(
                    student_record=record,
                    requirement=requirement,
                    reason=reason,
                    requested_by_id=staff.pk,
                    requested_at=now(),
                )
        except IntegrityError:
            raise ValidationError(
                {"requirement": _("A pending or approved waiver already exists for this requirement.")}
            ) from None
        audit(
            "graduation.waiver_requested",
            waiver,
            reason=reason,
            properties={"student_number": record.student_number, "requirement_id": requirement.pk},
            causer=staff,
        )
        return waiver

    def approve(
        self, waiver: DegreeRequirementWaiver, approver: Any, note: str | None = None
    ) -> DegreeRequirementWaiver:
        self._authorize_decision(waiver, approver)
        note = (note or "").strip() or None
        self._decide(waiver, WaiverStatus.APPROVED, approver, note)
        audit("graduation.waiver_approved", waiver, reason=note, properties=self._properties(waiver), causer=approver)
        return waiver

    def reject(self, waiver: DegreeRequirementWaiver, approver: Any, note: str) -> DegreeRequirementWaiver:
        self._authorize_decision(waiver, approver)
        note = require_reason(note, "note")
        self._decide(waiver, WaiverStatus.REJECTED, approver, note)
        audit("graduation.waiver_rejected", waiver, reason=note, properties=self._properties(waiver), causer=approver)
        return waiver

    def lift(self, waiver: DegreeRequirementWaiver, staff: Any, reason: str) -> DegreeRequirementWaiver:
        authorize(staff, waiver.student_record, Permission.GRADUATION_PROCESS)
        if waiver.status != WaiverStatus.APPROVED:
            raise ValidationError({"status": _("Only an approved waiver can be lifted.")})
        reason = require_reason(reason)
        waiver.status = WaiverStatus.LIFTED
        waiver.lifted_by_id = staff.pk
        waiver.lifted_at = now()
        waiver.lift_reason = reason
        waiver.save(update_fields=["status", "lifted_by", "lifted_at", "lift_reason", "updated_at"])
        audit("graduation.waiver_lifted", waiver, reason=reason, properties=self._properties(waiver), causer=staff)
        return waiver

    def can_decide(self, waiver: DegreeRequirementWaiver, user: Any) -> bool:
        """The screen's approve/reject buttons: pending, not one's own request, with the permission."""
        return bool(
            waiver.status == WaiverStatus.PENDING
            and waiver.requested_by_id != user.pk
            and user.has_perm(str(Permission.GRADUATION_PROCESS))
        )

    def can_lift(self, waiver: DegreeRequirementWaiver, user: Any) -> bool:
        return bool(waiver.status == WaiverStatus.APPROVED and user.has_perm(str(Permission.GRADUATION_PROCESS)))

    @staticmethod
    def _decide(waiver: DegreeRequirementWaiver, status: WaiverStatus, approver: Any, note: str | None) -> None:
        waiver.status = status
        waiver.decided_by_id = approver.pk
        waiver.decided_at = now()
        waiver.decision_note = note
        waiver.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])

    @staticmethod
    def _properties(waiver: DegreeRequirementWaiver) -> dict[str, Any]:
        return {"student_record_id": waiver.student_record_id, "requirement_id": waiver.requirement_id}

    @staticmethod
    def _authorize_decision(waiver: DegreeRequirementWaiver, approver: Any) -> None:
        authorize(approver, waiver.student_record, Permission.GRADUATION_PROCESS)
        if waiver.status != WaiverStatus.PENDING:
            raise ValidationError({"status": _("The request is already decided.")})
        if waiver.requested_by_id == approver.pk:
            raise ValidationError({"status": _("You cannot decide your own waiver request.")})
