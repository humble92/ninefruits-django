"""Graduation (original ``GraduateStudents``; legacy: status code Z with no check): the latest
stored primary audit must be satisfied; then the graduation status change is recorded with the
date and a degree number is issued. One transaction per student, so a batch reports each
outcome.

The writes run in the system database context once the checks pass (``graduation.process``, the
record visible, the ``student_status_changes.approve`` scope checked by ``RecordStatusChange``):
the status change updates ``student_records``, which row level security leaves to
``student_records.manage``, and graduation staff need not hold it. The initiating user stays in
``app.user_id``, so the data audit names them."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.core.db import session_context
from ninefruits.curriculum.enums import ProgramRole
from ninefruits.graduation.models import DegreeAudit
from ninefruits.graduation.services import DegreeNumberGenerator
from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentRecord, StudentStatusChangeType
from ninefruits.security.enums import Permission

from ._support import authorize


class GraduateStudents:
    def __init__(self, status_change: Any | None = None, numbers: DegreeNumberGenerator | None = None) -> None:
        from ninefruits.person.actions import RecordStatusChange

        self.status_change = status_change or RecordStatusChange()
        self.numbers = numbers or DegreeNumberGenerator()

    def handle(self, record: StudentRecord, graduation_date: date, staff: Any, reason: str) -> StudentRecord:
        authorize(staff, record, Permission.GRADUATION_PROCESS)
        if record.status != StudentStatus.ENROLLED:
            raise ValidationError({"status": _("Only an enrolled student can graduate.")})
        latest = (
            DegreeAudit.objects.filter(student_record_id=record.pk, program_role=ProgramRole.PRIMARY)
            .order_by("-id")
            .first()
        )
        if latest is None:
            raise ValidationError({"audit": _("No stored degree audit: run the audit first.")})
        if not latest.is_satisfied:
            raise ValidationError({"audit": _("The latest degree audit is not satisfied.")})
        change_type = StudentStatusChangeType.objects.get(code="graduation")

        with transaction.atomic(), session_context().system("graduation.graduate"):
            self.status_change.handle(record, change_type, graduation_date, reason, staff)
            record.degree_number = self.numbers.next(record.program, graduation_date)
            record.save(update_fields=["degree_number", "updated_at"])
            audit(
                "graduation.processed",
                record,
                reason=reason,
                properties={
                    "student_number": record.student_number,
                    "graduation_date": graduation_date.isoformat(),
                    "degree_number": record.degree_number,
                    "audit_id": latest.pk,
                },
                causer=staff,
            )
        return record

    __call__ = handle

    def batch(self, records: Iterable[StudentRecord], graduation_date: date, staff: Any, reason: str) -> dict[str, Any]:
        """``{"graduated": n, "errors": ["<student number>: <message>", ...]}``."""
        summary: dict[str, Any] = {"graduated": 0, "errors": []}
        for record in records:
            try:
                self.handle(record, graduation_date, staff, reason)
            except ValidationError as error:
                summary["errors"].append(f"{record.student_number}: {' '.join(error.messages)}")
            else:
                summary["graduated"] += 1
        return summary
