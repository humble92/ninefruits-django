"""Closes a term (original ``term:close``): term records, academic standing, honors, then grades
closed. The work runs in the queue (a Celery chord, progress on the term record screen); a dry run
only checks whether the term can close. Exit code 2 when grades are not final yet."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser
from django.db import transaction

from ninefruits.core.commands import AuditedCommand
from ninefruits.grading.actions import CloseTerm
from ninefruits.term.enums import TermStatus
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = "Close a term: term records, academic standing, honors, then grades closed (a queued batch)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("term", help="Term code, e.g. 2026-FA")
        parser.add_argument("--dry-run", action="store_true", help="Only check whether the term can close")
        parser.add_argument("--reason", help="Why (recorded with the close)")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        term = Term.objects.select_related("term_type").filter(code=options["term"]).first()
        if term is None:
            self.error("Unknown term code.")
            return self.FAILURE

        close = CloseTerm()
        preflight = close.preflight(term)
        self.info(f"{preflight.students} student(s) with finalized grades.")
        for entry in preflight.open_sections:
            self.warn(f"{entry.section.label()}: {entry.unfinished_count} grade(s) not finalized.")
        self.record_result({"students": preflight.students, "open_sections": len(preflight.open_sections)})

        if term.status != TermStatus.PUBLISHED:
            self.error(f"The term is {term.status}; only a published term closes.")
            return self.FAILURE
        if not preflight.is_ready():
            return self.PROBLEMS_FOUND
        if self.is_dry_run():
            self.info("Ready to close.")
            return self.SUCCESS

        with transaction.atomic():
            batch = close.close(term, self.actor(), options.get("reason") or None)
        if batch is not None:
            self.record_result({"batch": batch.pk})
        self.info("Close started. The term moves to grades closed when the batch finishes (see Flower).")
        return self.SUCCESS
