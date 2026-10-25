"""Registering a student for a session (original ``RegisterForAssessment``): by the student while
the window is open and seats remain, or by staff with ``assessments.record`` at any time before
the session (legacy cet_add*: no window, no capacity, duplicates refused by a unique key).
Cancelled registrations stay and can be reactivated.

Students have no write policy on registrations: the checks here stand in for it and the row is
written in the system context (ADR 0014, like course evaluation answers). Seats are counted with
the session row locked and in the system context, so the count covers every registration of the
session, not only those the acting user can see."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.assessment.enums import AssessmentRegistrationStatus
from ninefruits.assessment.models import AssessmentRegistration, AssessmentResult, AssessmentSession
from ninefruits.audit.logger import audit
from ninefruits.core.db import session_context
from ninefruits.person.enums import StudentStatus
from ninefruits.security.enums import Permission

from ._support import now


def _error(field: str, message: str) -> ValidationError:
    return ValidationError({field: message})


class RegisterForAssessment:
    def register(
        self, session: AssessmentSession, record: Any, actor: Any, by_staff: bool = False
    ) -> AssessmentRegistration:
        if by_staff:
            if not actor.has_perm(Permission.ASSESSMENTS_RECORD) or not record.is_visible_to(actor):
                raise PermissionDenied
        elif actor.person_id is None or record.person_id != actor.person_id:
            raise PermissionDenied

        session = AssessmentSession.objects.select_related("assessment_type").get(pk=session.pk)
        if not session.assessment_type.is_active:
            raise _error("session", _("This kind of examination is no longer held."))
        if not StudentStatus(record.status).is_active():
            raise _error("session", _("Only current students can register."))
        if not by_staff and not session.is_open_for_registration():
            raise _error("session", _("Registration for this session is closed."))
        # Nobody registers after the session date; a result needs a registration made before it.
        if session.held_date < timezone.localdate():
            raise _error("session", _("This session has already been held."))

        already = _("Already registered for this session.")
        try:
            with session_context().system("assessment:register"), transaction.atomic():
                AssessmentSession.objects.select_for_update().filter(pk=session.pk).first()
                existing = AssessmentRegistration.objects.filter(
                    session_id=session.pk, student_record_id=record.pk
                ).first()
                if existing is not None and existing.status != AssessmentRegistrationStatus.CANCELLED:
                    raise _error("session", already)
                if (
                    session.capacity is not None
                    and AssessmentRegistration.objects.filter(session_id=session.pk).active().count()
                    >= session.capacity
                ):
                    raise _error("session", _("This session is full."))
                registration = self._write(existing, session, record, actor, by_staff)
        except IntegrityError:
            raise _error("session", already) from None

        audit(
            "assessment.registered",
            registration,
            properties={"session_id": session.pk, "student_number": record.student_number, "by_staff": by_staff},
            causer=actor,
        )
        return registration

    def _write(
        self,
        existing: AssessmentRegistration | None,
        session: AssessmentSession,
        record: Any,
        actor: Any,
        by_staff: bool,
    ) -> AssessmentRegistration:
        registered_by_id = actor.pk if by_staff else None
        if existing is not None:
            existing.status = AssessmentRegistrationStatus.REGISTERED
            existing.registered_at = now()
            existing.registered_by_id = registered_by_id
            existing.cancelled_at = None
            existing.cancel_reason = None
            existing.save(
                update_fields=[
                    "status",
                    "registered_at",
                    "registered_by",
                    "cancelled_at",
                    "cancel_reason",
                    "updated_at",
                ]
            )
            return existing
        return AssessmentRegistration.objects.create(
            session_id=session.pk,
            student_record_id=record.pk,
            registered_at=now(),
            registered_by_id=registered_by_id,
        )

    def is_staff_for(self, registration: AssessmentRegistration, actor: Any) -> bool:
        return bool(actor.has_perm(Permission.ASSESSMENTS_RECORD) and registration.student_record.is_visible_to(actor))

    def cancel(
        self, registration: AssessmentRegistration, actor: Any, reason: str | None = None
    ) -> AssessmentRegistration:
        registration = AssessmentRegistration.objects.select_related("session", "student_record").get(
            pk=registration.pk
        )
        by_staff = self.is_staff_for(registration, actor)
        if not by_staff and (actor.person_id is None or registration.student_record.person_id != actor.person_id):
            raise PermissionDenied
        if registration.status == AssessmentRegistrationStatus.CANCELLED:
            raise _error("registration", _("This registration is already cancelled."))
        if not by_staff and not registration.session.is_open_for_registration():
            raise _error("registration", _("Registration for this session is closed."))

        reason = (reason or "").strip() or None
        # Checked and written in the system context: a student cannot see an unpublished result.
        with session_context().system("assessment:cancel"), transaction.atomic():
            if AssessmentResult.objects.filter(registration_id=registration.pk).exists():
                raise _error("registration", _("A result has been entered; the registration cannot be cancelled."))
            registration.status = AssessmentRegistrationStatus.CANCELLED
            registration.cancelled_at = now()
            registration.cancel_reason = reason
            registration.save(update_fields=["status", "cancelled_at", "cancel_reason", "updated_at"])

        audit(
            "assessment.registration_cancelled",
            registration,
            reason=reason,
            properties={"session_id": registration.session_id},
            causer=actor,
        )
        return registration

    def mark_absent(self, registration: AssessmentRegistration, staff: Any) -> AssessmentRegistration:
        if not staff.has_perm(Permission.ASSESSMENTS_RECORD):
            raise PermissionDenied
        if registration.status != AssessmentRegistrationStatus.REGISTERED:
            raise _error("registration", _("The student is not registered for this session."))
        registration.status = AssessmentRegistrationStatus.ABSENT
        registration.save(update_fields=["status", "updated_at"])
        audit("assessment.absent", registration, properties={"session_id": registration.session_id}, causer=staff)
        return registration
