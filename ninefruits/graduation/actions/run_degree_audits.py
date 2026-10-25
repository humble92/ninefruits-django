"""Stores audits (original ``RunDegreeAudits``): for one student (the screen's "save audit") or
for every enrolled student, optionally from a year level or one student number (the command and
the "Run audits" button). Each run adds a snapshot; the newest is the one graduation reads."""

from __future__ import annotations

from typing import Any

from django.db import transaction

from ninefruits.audit.logger import audit
from ninefruits.graduation.data import DegreeAuditResult
from ninefruits.graduation.models import DegreeAudit as StoredAudit
from ninefruits.graduation.services import DegreeAudit
from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import StudentRecord
from ninefruits.security.enums import Permission

from ._support import authorize, now


class RunDegreeAudits:
    def __init__(self, audit_service: DegreeAudit | None = None) -> None:
        self.audit = audit_service or DegreeAudit()

    def for_record(self, record: StudentRecord, staff: Any | None, term: Any | None = None) -> list[StoredAudit]:
        """One snapshot per program of the student (primary first). ``staff`` is checked for
        ``graduation.audit`` and the record's visibility; ``None`` is a system run."""
        if staff is not None:
            authorize(staff, record, Permission.GRADUATION_AUDIT)
        with transaction.atomic():
            return [self._store(record, result, staff, term) for result in self.audit.evaluate_all(record)]

    def for_all(
        self,
        term: Any | None,
        staff: Any | None,
        minimum_year_level: int | None = None,
        student_number: str | None = None,
    ) -> dict[str, int]:
        """Every enrolled student (or those at or above the year level, or one student);
        returns ``{"students": n, "satisfied": n}`` counted on the primary program."""
        summary = {"students": 0, "satisfied": 0}
        records = StudentRecord.objects.filter(status=StudentStatus.ENROLLED).select_related("program")
        if minimum_year_level is not None:
            records = records.filter(year_level__gte=minimum_year_level)
        if student_number is not None:
            records = records.filter(student_number=student_number)
        for record in records.order_by("id").iterator(chunk_size=200):
            primary = self.for_record(record, None, term)[0]
            summary["students"] += 1
            summary["satisfied"] += 1 if primary.is_satisfied else 0
        if staff is not None:
            audit("graduation.audits_run", term, properties=summary, causer=staff)
        return summary

    def _store(
        self, record: StudentRecord, result: DegreeAuditResult, staff: Any | None, term: Any | None
    ) -> StoredAudit:
        return StoredAudit.objects.create(
            student_record=record,
            requirement_set=result.requirement_set,
            program_role=result.role,
            program=result.program,
            term=term,
            is_satisfied=result.is_satisfied(),
            earned_credits=result.earned_credits,
            required_credits=result.required_credits,
            cumulative_gpa=result.cumulative_gpa,
            result=result.to_dict(),
            audited_at=now(),
            audited_by_id=getattr(staff, "pk", None),
        )
