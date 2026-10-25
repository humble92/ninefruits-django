"""Turning confirmed applicants into students (original ``MatriculateApplicant``) and expiring
drafts (original ``ExpireDraftApplications``)."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import Application
from ninefruits.admission.settings import AdmissionSettings
from ninefruits.audit.logger import audit
from ninefruits.core.db import session_context
from ninefruits.person.actions import RegisterStudent
from ninefruits.person.models import StudentRecord
from ninefruits.security.enums import Permission


class MatriculateApplicant:
    """Turns a confirmed applicant into a student: a new student record with a new student
    number in the admission term (porting-plan 10.1). The person and the account stay the same,
    so the applicant signs in as a student with the same login. A graduate applying again keeps
    the earlier record.

    Admissions staff may not manage student records, so the record is created as a system actor
    after checking ``applications.matriculate`` (the audit still names the staff member; ADR
    0008)."""

    def __init__(self, register_student: RegisterStudent | None = None) -> None:
        self.register_student = register_student or RegisterStudent()

    def handle(self, application: Application, admission_term: Any, matriculated_by: Any) -> StudentRecord:
        if not application.is_in_scope_of(matriculated_by, Permission.APPLICATIONS_MATRICULATE):
            raise PermissionDenied
        ensure_ready(application)

        with session_context().system("matriculation"), transaction.atomic():
            record = self.register_student.handle(
                application.person,
                application.program,
                {
                    "admission_date": admission_term.start_date,
                    "admission_term_id": admission_term.pk,
                    "admission_type_id": application.admission_type_id,
                },
                matriculated_by,
            )
            application.student_record = record
            application.matriculated_at = timezone.now()
            application.save(update_fields=["student_record", "matriculated_at", "updated_at"])
            audit(
                "application.matriculated",
                application,
                properties={
                    "student_record_id": record.pk,
                    "student_number": record.student_number,
                    "term": admission_term.code,
                },
                causer=matriculated_by,
            )
        return record

    __call__ = handle


def ensure_ready(application: Application) -> None:
    if application.status != ApplicationStatus.CONFIRMED or application.student_record_id is not None:
        raise ValidationError({"status": _("Only accepted offers without a student record can be matriculated.")})


class ExpireDraftApplications:
    """Drafts in a closed cycle, or untouched for the configured number of days, become expired
    so they no longer block a new application. Runs from the scheduler (``admission.expire_drafts``)
    as a system actor."""

    def __init__(self, settings: AdmissionSettings | None = None) -> None:
        self._settings = settings

    def query(self, at: datetime | None = None) -> QuerySet[Application]:
        at = at or timezone.now()
        settings = self._settings or AdmissionSettings.load()
        stale_before = at - timedelta(days=max(1, settings.draft_expiry_days))
        return Application.objects.filter(status=ApplicationStatus.DRAFT).filter(
            Q(updated_at__lt=stale_before)
            | Q(admission_cycle__closes_at__isnull=False, admission_cycle__closes_at__lte=at)
        )

    def handle(self, at: datetime | None = None) -> int:
        return self.query(at).update(status=ApplicationStatus.EXPIRED, updated_at=timezone.now())

    __call__ = handle
