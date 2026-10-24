"""Records the results of a session from a CSV (original ``assessment:import-results``), with the
same rules as the admin screen. Requires ``--actor``: results are recorded under that account."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

from django.core.management.base import CommandParser

from ninefruits.assessment.models import AssessmentSession
from ninefruits.assessment.services import AssessmentResultImporter
from ninefruits.core.commands import AuditedCommand


def find_session(type_code: str, held_date: str) -> AssessmentSession | None:
    try:
        day = date.fromisoformat(held_date)
    except ValueError:
        return None
    return (
        AssessmentSession.objects.select_related("assessment_type")
        .filter(assessment_type__code=type_code, held_date=day)
        .first()
    )


class Command(AuditedCommand):
    help = "Record the results of a session from a CSV (same rules as the admin screen). Requires --actor."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("type", help="Kind code")
        parser.add_argument("held_date", help="Session date (YYYY-MM-DD)")
        parser.add_argument("file", help="CSV with student_number and a column per area code")
        parser.add_argument("--dry-run", action="store_true", help="Check the rows without recording")

    def handle(self, *args: Any, **options: Any) -> int:
        session = find_session(options["type"], options["held_date"])
        path = Path(options["file"])
        actor = self.actor()
        if session is None:
            self.error("Unknown session: give the kind code and the session date.")
            return self.FAILURE
        if not path.is_file() or not os.access(path, os.R_OK):
            self.error(f"Cannot read [{path}].")
            return self.FAILURE
        if actor is None:
            self.error("--actor is required: results are recorded under that account.")
            return self.FAILURE

        dry_run = self.is_dry_run()
        summary = AssessmentResultImporter().import_file(session, path, actor, dry_run)
        self.record_result(
            {
                "session_id": session.pk,
                "file": path.name,
                "rows": summary.rows,
                "recorded": summary.recorded,
                "absent": summary.absent,
                "errors": len(summary.errors),
            }
        )
        for error in summary.errors:
            self.warn(error)
        prefix = "Dry run: " if dry_run else ""
        self.info(
            f"{prefix}{summary.rows} row(s): {summary.recorded} recorded, {summary.absent} absent, "
            f"{len(summary.errors)} error(s)."
        )
        return self.SUCCESS if not summary.errors else self.PROBLEMS_FOUND
