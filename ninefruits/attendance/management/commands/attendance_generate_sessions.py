"""Creates the class meetings of a term from the sections' weekly meeting times (original
``attendance:generate-sessions``). Existing meetings and their attendance are kept, so running it
again after the meeting times change only adds what is missing."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.attendance.actions import GenerateClassMeetings
from ninefruits.core.commands import AuditedCommand
from ninefruits.offering.enums import SectionStatus
from ninefruits.offering.models import Section
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = "Create the class meetings of a term from the sections' weekly meeting times (existing meetings are kept)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("term", help="Term code")
        parser.add_argument(
            "--section", help="Only this section (course code-section code, e.g. CSE2010-01)", default=None
        )
        parser.add_argument("--dry-run", action="store_true", help="Count only")

    def handle(self, *args: Any, **options: Any) -> int:
        term = Term.objects.filter(code=options["term"]).first()
        if term is None:
            self.error("Unknown term code.")
            return self.FAILURE

        sections = Section.objects.filter(term_id=term.pk).exclude(status=SectionStatus.CANCELLED)
        if options.get("section"):
            course_code, _dash, section_code = str(options["section"]).partition("-")
            sections = sections.filter(course__code=course_code)
            if section_code:
                sections = sections.filter(section_code=section_code)

        if self.is_dry_run():
            self.info(f"Dry run: {sections.count()} section(s) would be processed.")
            return self.SUCCESS

        generate = GenerateClassMeetings()
        summary = {"sections": 0, "created": 0}
        for section in sections.order_by("id").iterator(chunk_size=500):
            summary["created"] += generate.for_section(section, None)
            summary["sections"] += 1

        self.record_result({"term": term.code, **summary})
        self.info(f"{summary['sections']} section(s): {summary['created']} meeting(s) created.")
        return self.SUCCESS
