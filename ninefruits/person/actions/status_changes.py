"""Student status changes (original ``RequestStatusChange``, ``DecideStatusChange``,
``RecordStatusChange`` and ``CancelStatusChange``).

A student asks for a change of their own record and staff decide it, or staff record a change
directly (approved at once). The requester never decides their own request (separation of
duties), and approval is refused when the record's status changed after the request."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.person.enums import StatusChangeStatus, StudentStatus
from ninefruits.person.models import StudentRecord, StudentStatusChange, StudentStatusChangeType
from ninefruits.security.enums import Permission
from ninefruits.security.services.authorization import authorization


def _now() -> Any:
    return timezone.now().replace(microsecond=0)


def ensure_applies(change_type: StudentStatusChangeType, record: StudentRecord) -> None:
    if not change_type.applies_from(record.status):
        raise ValidationError(
            {
                "status_change_type_id": _("This change does not apply to a student who is %(status)s.")
                % {"status": StudentStatus(record.status).label}
            }
        )


def ensure_approver_scope(user: Any, record: StudentRecord) -> None:
    scope = authorization().scope_for(user, Permission.STUDENT_STATUS_CHANGES_APPROVE)
    if not (scope.is_global or record.org_unit_id in scope.org_unit_ids or record.program_id in scope.program_ids):
        raise PermissionDenied


def apply_status(record: StudentRecord, status: StudentStatus | str, effective_date: date) -> None:
    """Sets the record status. Graduation also sets the graduation date."""
    status = StudentStatus(status)
    record.status = status
    record.status_changed_at = _now()
    if status == StudentStatus.GRADUATED:
        record.graduation_date = effective_date
    record.save(update_fields=["status", "status_changed_at", "graduation_date", "updated_at"])


class RequestStatusChange:
    def handle(
        self,
        record: StudentRecord,
        change_type: StudentStatusChangeType,
        effective_date: date,
        reason: str,
        student: Any,
        term_id: int | None = None,
    ) -> StudentStatusChange:
        if record.person_id != student.person_id:
            raise ValidationError({"student_record_id": _("You can only make requests for your own record.")})
        if not change_type.can_student_request or not change_type.is_active:
            raise ValidationError({"status_change_type_id": _("Students cannot request this type of change.")})
        ensure_applies(change_type, record)

        try:
            # Own savepoint: on PostgreSQL a failed statement would abort the caller's transaction.
            with transaction.atomic():
                change = StudentStatusChange.objects.create(
                    student_record=record,
                    type=change_type,
                    from_status=record.status,
                    to_status=change_type.to_status,
                    effective_date=effective_date,
                    term_id=term_id,
                    reason=reason,
                    requested_by=student,
                    requested_at=_now(),
                )
        except IntegrityError as error:
            raise ValidationError(
                {"status_change_type_id": _("There is already a pending request for this record.")}
            ) from error

        audit(
            "student_status_change.requested",
            change,
            reason=reason,
            properties={"type": change_type.code},
            causer=student,
        )
        return change

    __call__ = handle


class DecideStatusChange:
    def approve(self, change: StudentStatusChange, approver: Any, note: str | None = None) -> StudentStatusChange:
        return self._decide(change, approver, StatusChangeStatus.APPROVED, note)

    def reject(self, change: StudentStatusChange, approver: Any, note: str) -> StudentStatusChange:
        return self._decide(change, approver, StatusChangeStatus.REJECTED, note)

    def _decide(
        self, change: StudentStatusChange, approver: Any, decision: StatusChangeStatus, note: str | None
    ) -> StudentStatusChange:
        if change.status != StatusChangeStatus.REQUESTED:
            raise ValidationError({"status": _("This request has already been decided.")})
        if change.requested_by_id == approver.pk:
            raise PermissionDenied(_("You cannot decide a request you made yourself."))

        record = StudentRecord.objects.get(pk=change.student_record_id)
        ensure_approver_scope(approver, record)

        with transaction.atomic():
            if decision == StatusChangeStatus.APPROVED:
                if record.status != change.from_status:
                    raise ValidationError(
                        {
                            "status": _(
                                "The student's status changed after the request was made. Reject it and ask for a "
                                "new request."
                            )
                        }
                    )
                apply_status(record, change.to_status, change.effective_date)

            change.status = decision
            change.decided_by = approver
            change.decided_at = _now()
            change.decision_note = note
            change.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])

            audit(
                f"student_status_change.{decision.value}",
                change,
                reason=note,
                properties={"student_record_id": record.pk, "from": change.from_status, "to": change.to_status},
                causer=approver,
            )
        return change


class RecordStatusChange:
    """Staff record a change directly (e.g. dismissal, or a request received on paper). The
    change is approved at once by the staff member, who needs the approve permission for the
    record; a reason is required."""

    def handle(
        self,
        record: StudentRecord,
        change_type: StudentStatusChangeType,
        effective_date: date,
        reason: str,
        staff: Any,
        term_id: int | None = None,
    ) -> StudentStatusChange:
        ensure_approver_scope(staff, record)
        ensure_applies(change_type, record)

        with transaction.atomic():
            now = _now()
            change = StudentStatusChange.objects.create(
                student_record=record,
                type=change_type,
                from_status=record.status,
                to_status=change_type.to_status,
                effective_date=effective_date,
                term_id=term_id,
                reason=reason,
                requested_by=staff,
                requested_at=now,
                status=StatusChangeStatus.APPROVED,
                decided_by=staff,
                decided_at=now,
            )
            apply_status(record, change_type.to_status, effective_date)
            audit(
                "student_status_change.recorded",
                change,
                reason=reason,
                properties={
                    "student_record_id": record.pk,
                    "type": change_type.code,
                    "from": change.from_status,
                    "to": change.to_status,
                },
                causer=staff,
            )
        return change

    __call__ = handle


class CancelStatusChange:
    """The requester withdraws a pending request."""

    def handle(self, change: StudentStatusChange, user: Any) -> StudentStatusChange:
        if change.requested_by_id != user.pk:
            raise PermissionDenied
        if change.status != StatusChangeStatus.REQUESTED:
            raise ValidationError({"status": _("This request has already been decided.")})
        change.status = StatusChangeStatus.CANCELLED
        change.decided_at = _now()
        change.save(update_fields=["status", "decided_at", "updated_at"])
        audit("student_status_change.cancelled", change, causer=user)
        return change

    __call__ = handle
