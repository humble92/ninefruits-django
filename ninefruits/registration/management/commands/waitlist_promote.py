"""Promotes waiting students to free seats (original ``waitlist:promote``). Normally promotion
runs by itself when a seat is freed; this serves every waitlist (of a term) now: after a
capacity increase, and on schedule (hourly) to expire lists whose windows have closed. Rules are
checked again for every promotion."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.registration.services.waitlists import promote_all
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = "Promote waiting students to free seats (rules checked again); expire waitlists of closed windows"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("term", nargs="?", help="Term code; default: every term with waiting students")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        term_id = None
        if options.get("term"):
            term_id = Term.objects.filter(code=options["term"]).values_list("pk", flat=True).first()
            if term_id is None:
                self.error("Unknown term code.")
                return self.FAILURE
        totals = promote_all(term_id)
        self.record_result(totals)
        self.info(
            f"{totals['sections']} section(s): {totals['promoted']} promoted, {totals['removed']} removed, "
            f"{totals['expired']} expired."
        )
        return self.SUCCESS
