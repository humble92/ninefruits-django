"""Stores a degree audit for every enrolled student, or one, as the graduation screens read it
(original ``degree-audit:run``). Each run adds snapshots; graduation reads the newest."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.graduation.actions import RunDegreeAudits
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = "Store a degree audit for every enrolled student (or one), as the graduation screens read it"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--term", help="Term code the audits belong to", default=None)
        parser.add_argument("--student-number", help="One student", default=None)
        parser.add_argument(
            "--min-year-level", type=int, help="Only students at or above this year level", default=None
        )

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        term = None
        if options.get("term"):
            term = Term.objects.filter(code=options["term"]).first()
            if term is None:
                self.error("Unknown term code.")
                return self.FAILURE

        summary = RunDegreeAudits().for_all(
            term,
            self.actor(),
            options.get("min_year_level") or None,
            options.get("student_number") or None,
        )
        self.record_result(summary)
        self.info(f"{summary['students']} student(s) audited, {summary['satisfied']} satisfied.")
        return self.SUCCESS
