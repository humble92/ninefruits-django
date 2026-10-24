"""Drops (cancels) a registration while registration or add/drop is open for the student, or
withdraws it (W) during the session's withdrawal window (original ``DropEnrollment``). Rows are
kept with their status. Staff may do either at any time with a reason. The freed seat goes to
the waitlist (``EnrollmentDropped`` -> queued promotion after commit)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.core.events import dispatch
from ninefruits.registration.data import RegistrationContext
from ninefruits.registration.enums import AttemptAction, AttemptOutcome, EnrollmentStatus
from ninefruits.registration.events import EnrollmentDropped
from ninefruits.registration.models import Enrollment
from ninefruits.registration.services.attempt_log import AttemptLog
from ninefruits.registration.services.rule_engine import RegistrationRuleEngine
from ninefruits.registration.services.seat_allocator import SeatAllocator

from .enroll_student import is_own, now, reason_required


class DropEnrollment:
    def __init__(
        self,
        engine: RegistrationRuleEngine | None = None,
        seats: SeatAllocator | None = None,
        attempts: AttemptLog | None = None,
    ) -> None:
        self.engine = engine or RegistrationRuleEngine()
        self.seats = seats or SeatAllocator()
        self.attempts = attempts or AttemptLog()

    def drop(self, enrollment: Enrollment, actor: Any, reason: str | None = None) -> Enrollment:
        return self._end(enrollment, actor, reason, AttemptAction.DROP, EnrollmentStatus.DROPPED)

    def withdraw(self, enrollment: Enrollment, actor: Any, reason: str | None = None) -> Enrollment:
        return self._end(enrollment, actor, reason, AttemptAction.WITHDRAW, EnrollmentStatus.WITHDRAWN)

    def _end(
        self, enrollment: Enrollment, actor: Any, reason: str | None, action: AttemptAction, status: EnrollmentStatus
    ) -> Enrollment:
        if enrollment.status != EnrollmentStatus.ENROLLED:
            raise ValidationError({"status": _("This registration is not active.")})

        record = enrollment.student_record
        section = enrollment.section
        by_staff = not is_own(actor, record)
        if by_staff and not section.is_registration_manageable_by(actor):
            raise PermissionDenied
        if by_staff and not (reason or "").strip():
            raise reason_required()

        evaluation = self.engine.evaluate(RegistrationContext(record, section, action, now(), actor, by_staff))
        if evaluation.is_blocked():
            self.attempts.record(record, section, action, AttemptOutcome.REFUSED, evaluation, actor)
            raise ValidationError({"enrollment": evaluation.blocking_messages()})

        with transaction.atomic():
            locked = self.seats.lock(section.pk)
            at = now()
            enrollment.status = status
            if status == EnrollmentStatus.DROPPED:
                enrollment.dropped_at = at
            else:
                enrollment.withdrawn_at = at
            enrollment.changed_by_id = actor.pk
            enrollment.save(update_fields=["status", "dropped_at", "withdrawn_at", "changed_by", "updated_at"])
            self.seats.release(locked, enrollment)
            dispatch(EnrollmentDropped(enrollment))

        self.attempts.record(record, section, action, AttemptOutcome.SUCCEEDED, evaluation, actor)
        if by_staff:
            audit(f"enrollment.staff_{status.value}", enrollment, reason=reason, causer=actor)
        return enrollment
