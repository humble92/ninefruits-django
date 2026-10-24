"""Copies sections from an earlier term (original ``section:copy``, ``CopySections``)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.offering.actions import CopySections
from ninefruits.organization.models import OrgUnit
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = (
        "Copy sections (instructors, meetings, rooms, seat groups, syllabus drafts) from an earlier term. "
        "Requires --actor."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("from_term", metavar="from-term", help="Code of the term to copy from, e.g. 2026-FA")
        parser.add_argument("to_term", metavar="to-term", help="Code of the term to copy into")
        parser.add_argument(
            "--org-unit", action="append", default=[], help="Only sections offered by these unit codes (repeatable)"
        )
        parser.add_argument("--dry-run", action="store_true", help="Show what would be copied without saving")

    def handle(self, *args: Any, **options: Any) -> int:
        source = Term.objects.filter(code=options["from_term"]).first()
        target = Term.objects.filter(code=options["to_term"]).first()
        actor = self.actor()
        if source is None or target is None:
            self.error("Unknown term code.")
            return self.FAILURE
        if actor is None:
            self.error("--actor is required: sections are copied within that account's scope.")
            return self.FAILURE

        units = options.get("org_unit") or []
        unit_ids = list(OrgUnit.objects.filter(code__in=units).values_list("pk", flat=True)) if units else None
        try:
            report = CopySections()(source, target, actor, unit_ids, dry_run=self.is_dry_run())
        except ValidationError as error:
            for message in error.messages:
                self.error(message)
            return self.FAILURE
        self.record_result({"from": source.code, "to": target.code, **report.summary()})

        for label, reason in report.skipped.items():
            self.stdout.write(f"  skipped {label}: {reason}")
        for label, notes in report.notes.items():
            self.stdout.write(f"  note {label}: {'; '.join(notes)}")
        summary = report.summary()
        self.info(
            f"{'Dry run: ' if self.is_dry_run() else ''}{summary['created']} section(s) copied, "
            f"{summary['skipped']} skipped, {summary['with_notes']} with notes."
        )
        return self.SUCCESS
