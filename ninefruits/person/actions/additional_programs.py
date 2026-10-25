"""Second majors and minors (original ``RequestAdditionalProgram``,
``DecideAdditionalProgramRequest``, ``CancelAdditionalProgramRequest`` and
``EndAdditionalProgram``).

A student applies during an open "second major and minor applications" term window (which may
be limited by year level etc.). The program must accept the kind, and the student stays within
the institution's limits (``student_records.max_second_majors``/``max_minors``). Staff of the
target program (``additional_programs.approve`` in its scope) decide; approval adds a
``student_record_programs`` row from the start of the request's term."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.organization.models import Program
from ninefruits.person.enums import AdditionalProgramRequestStatus, AdditionalProgramRole, StudentStatus
from ninefruits.person.models import AdditionalProgramRequest, StudentRecord, StudentRecordProgram
from ninefruits.person.settings import StudentRecordSettings
from ninefruits.term.enums import TermWindowType
from ninefruits.term.services.term_resolver import TermResolver


def _now() -> Any:
    return timezone.now().replace(microsecond=0)


def ensure_allowed(
    record: StudentRecord,
    program: Program,
    role: AdditionalProgramRole | str,
    settings: StudentRecordSettings,
    ignore_request_id: int | None = None,
) -> None:
    """Checked when the student applies and again when staff approve."""
    role = AdditionalProgramRole(role)
    accepts = program.allows_second_major if role == AdditionalProgramRole.SECOND_MAJOR else program.allows_minor
    if not accepts or not program.is_effective_on():
        raise ValidationError({"program_id": _("This program does not accept that kind of application.")})
    if program.pk == record.program_id or record.current_programs().filter(program=program).exists():
        raise ValidationError({"program_id": _("You already follow this program.")})

    held = record.current_programs().filter(role=role).count()
    pending = AdditionalProgramRequest.objects.filter(
        student_record=record, role=role, status=AdditionalProgramRequestStatus.REQUESTED
    )
    if ignore_request_id is not None:
        pending = pending.exclude(pk=ignore_request_id)
    limit = settings.max_second_majors if role == AdditionalProgramRole.SECOND_MAJOR else settings.max_minors
    if held + pending.count() >= limit:
        raise ValidationError(
            {"role": _("You can have at most %(count)s at a time (including pending applications).") % {"count": limit}}
        )


class RequestAdditionalProgram:
    def __init__(self, terms: TermResolver | None = None) -> None:
        self.terms = terms or TermResolver()

    def handle(
        self,
        record: StudentRecord,
        program: Program,
        role: AdditionalProgramRole | str,
        statement: str | None,
        student: Any,
    ) -> AdditionalProgramRequest:
        role = AdditionalProgramRole(role)
        if record.person_id != student.person_id:
            raise ValidationError({"student_record_id": _("You can only make requests for your own record.")})
        if not StudentStatus(record.status).is_active():
            raise ValidationError({"student_record_id": _("Only current students can apply.")})
        terms = self.terms.terms_open_for(TermWindowType.ADDITIONAL_PROGRAM_APPLICATION, record)
        if not terms:
            raise ValidationError(
                {"program_id": _("Applications for a second major or minor are not open for you now.")}
            )
        ensure_allowed(record, program, role, StudentRecordSettings.load())

        try:
            # Own savepoint: on PostgreSQL a failed statement would abort the caller's transaction.
            with transaction.atomic():
                request = AdditionalProgramRequest.objects.create(
                    student_record=record,
                    program=program,
                    org_unit_id=program.org_unit_id,
                    role=role,
                    term=terms[0],
                    statement=statement or None,
                    requested_by=student,
                    requested_at=_now(),
                )
        except IntegrityError as error:
            raise ValidationError(
                {"program_id": _("There is already a pending application for this program.")}
            ) from error

        audit(
            "additional_program.requested",
            request,
            reason=statement or None,
            properties={"program": program.code, "role": role.value},
            causer=student,
        )
        return request

    __call__ = handle


class DecideAdditionalProgramRequest:
    def approve(
        self, request: AdditionalProgramRequest, approver: Any, note: str | None = None
    ) -> StudentRecordProgram:
        self._ensure_decidable(request, approver)
        ensure_allowed(request.student_record, request.program, request.role, StudentRecordSettings.load(), request.pk)
        with transaction.atomic():
            program = StudentRecordProgram.objects.create(
                student_record_id=request.student_record_id,
                program_id=request.program_id,
                role=request.role,
                start_date=request.term.start_date,
            )
            request.status = AdditionalProgramRequestStatus.APPROVED
            request.decided_by = approver
            request.decided_at = _now()
            request.decision_note = note or None
            request.student_record_program = program
            request.save()
            audit(
                "additional_program.approved",
                request,
                reason=note or None,
                properties={"student_record_program_id": program.pk},
                causer=approver,
            )
        return program

    def reject(self, request: AdditionalProgramRequest, approver: Any, note: str) -> AdditionalProgramRequest:
        self._ensure_decidable(request, approver)
        request.status = AdditionalProgramRequestStatus.REJECTED
        request.decided_by = approver
        request.decided_at = _now()
        request.decision_note = note
        request.save(update_fields=["status", "decided_by", "decided_at", "decision_note", "updated_at"])
        audit("additional_program.rejected", request, reason=note, causer=approver)
        return request

    @staticmethod
    def _ensure_decidable(request: AdditionalProgramRequest, approver: Any) -> None:
        if not request.is_decidable_by(approver):
            raise PermissionDenied
        if request.status != AdditionalProgramRequestStatus.REQUESTED:
            raise ValidationError({"status": _("This request has already been decided.")})
        if request.requested_by_id == approver.pk:
            raise PermissionDenied(_("You cannot decide a request you made yourself."))


class CancelAdditionalProgramRequest:
    def handle(self, request: AdditionalProgramRequest, student: Any) -> AdditionalProgramRequest:
        if request.student_record.person_id != student.person_id:
            raise PermissionDenied
        if request.status != AdditionalProgramRequestStatus.REQUESTED:
            raise ValidationError({"status": _("This request has already been decided.")})
        request.status = AdditionalProgramRequestStatus.CANCELLED
        request.save(update_fields=["status", "updated_at"])
        audit("additional_program.request_cancelled", request, causer=student)
        return request

    __call__ = handle


class EndAdditionalProgram:
    """Ends a second major or minor (given up, or not completed). The registrar (records in
    scope) or staff of the program (approval scope) do this with a reason."""

    def handle(self, program: StudentRecordProgram, end_date: date, reason: str, user: Any) -> StudentRecordProgram:
        record = program.student_record
        if not record.is_manageable_by(user) and not program.program.is_additional_program_decidable_by(user):
            raise PermissionDenied
        if program.end_date is not None or end_date < program.start_date:
            raise ValidationError({"end_date": _("This program has already ended, or the date is before it started.")})
        program.end_date = end_date
        program.save(update_fields=["end_date", "updated_at"])
        audit(
            "additional_program.ended", program, reason=reason, properties={"student_record_id": record.pk}, causer=user
        )
        return program

    __call__ = handle
