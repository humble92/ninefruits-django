"""Results of a session from a CSV (original ``AssessmentResultImporter``): one row per student
with ``student_number``, a column per area code (or ``total`` for kinds without areas), optional
``passed`` (Y/N, pass/fail kinds), ``absent`` (Y) and ``note``. Column names are matched
case-insensitively. Rows of students not registered for the session are reported and skipped: a
result needs a registration made before the session (legacy bulk entry silently added them).
The admin screen and ``assessment_import_results`` share this service.

The original reports problems in English (operator output); so does this port."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

from django.core.exceptions import ValidationError

from ninefruits.assessment.actions import RecordAssessmentResult, RegisterForAssessment
from ninefruits.assessment.actions._support import to_decimal
from ninefruits.assessment.enums import AssessmentRegistrationStatus
from ninefruits.assessment.models import AssessmentRegistration, AssessmentSession

YES = frozenset({"y", "yes", "1", "true", "p", "pass"})


@dataclass(slots=True)
class ImportSummary:
    rows: int = 0
    recorded: int = 0
    absent: int = 0
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"rows": self.rows, "recorded": self.recorded, "absent": self.absent, "errors": list(self.errors)}


def is_yes(value: Any) -> bool:
    return str(value if value is not None else "").strip().lower() in YES


def read_rows(source: str | Path | bytes | IO[bytes]) -> tuple[list[str], list[dict[str, str]]]:
    """The lowercased header and the rows (keys lowercased) of a UTF-8 CSV (BOM allowed)."""
    if isinstance(source, str | Path):
        data = Path(source).read_bytes()
    elif isinstance(source, bytes):
        data = source
    else:
        data = source.read()
    text = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    try:
        header = [column.strip().lower() for column in next(reader)]
    except StopIteration:
        return [], []
    rows = []
    for values in reader:
        if not any(value.strip() for value in values):
            continue
        rows.append({column: (values[index] if index < len(values) else "") for index, column in enumerate(header)})
    return header, rows


class AssessmentResultImporter:
    def __init__(
        self, results: RecordAssessmentResult | None = None, registrations: RegisterForAssessment | None = None
    ) -> None:
        self.results = results or RecordAssessmentResult()
        self.registrations = registrations or RegisterForAssessment()

    def import_file(
        self, session: AssessmentSession, source: str | Path | bytes | IO[bytes], staff: Any, dry_run: bool = False
    ) -> ImportSummary:
        from ninefruits.person.models import StudentRecord

        session = AssessmentSession.objects.select_related("assessment_type").get(pk=session.pk)
        # Lowercase column => component code (scores are keyed back by the code).
        codes = {component.code.lower(): component.code for component in session.assessment_type.ordered_components()}
        summary = ImportSummary()
        header, rows = read_rows(source)
        if "student_number" not in header:
            summary.errors.append("Missing column: student_number")
            return summary

        # Line numbers count the header (the first data row is line 2).
        for line, row in enumerate(rows, start=2):
            summary.rows += 1
            number = (row.get("student_number") or "").strip()
            record = StudentRecord.objects.filter(student_number=number).first() if number else None
            if record is None:
                summary.errors.append(f"Line {line}: unknown student number [{number}].")
                continue
            registration = (
                AssessmentRegistration.objects.filter(session_id=session.pk, student_record_id=record.pk)
                .exclude(status=AssessmentRegistrationStatus.CANCELLED)
                .first()
            )
            if registration is None:
                summary.errors.append(f"Line {line}: [{number}] is not registered for this session.")
                continue
            absent = is_yes(row.get("absent"))
            try:
                if dry_run:
                    if not absent:
                        self._validate(row, codes)
                    if absent:
                        summary.absent += 1
                    else:
                        summary.recorded += 1
                    continue
                if absent:
                    self.registrations.mark_absent(registration, staff)
                    summary.absent += 1
                    continue
                scores = {code: row.get(column) for column, code in codes.items()}
                passed_cell = (row.get("passed") or "").strip()
                passed = is_yes(passed_cell) if passed_cell else None
                total = to_decimal(row.get("total"))
                note = (row.get("note") or "").strip() or None
                self.results.for_registration(registration, scores, passed, staff, total, note)
                summary.recorded += 1
            except ValidationError as error:
                summary.errors.append(f"Line {line}: " + " ".join(str(message) for message in error.messages))
        return summary

    def _validate(self, row: dict[str, str], codes: dict[str, str]) -> None:
        for column, code in codes.items():
            if to_decimal(row.get(column)) is None:
                raise ValidationError({"scores": f"Missing or non-numeric score for [{code}]."})
