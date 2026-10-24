"""Pushes published sections (course, instructors, enrolled students) to an LMS platform
(original ``lms:sync``). Sections already linked are only ensured again (idempotent)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.lms.actions import SyncSection, current_sections
from ninefruits.lms.models import LmsPlatform
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = "Push published sections (course, instructors, enrolled students) to an LMS platform"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("platform", help="Platform code")
        parser.add_argument("--term", default=None, help="Term code (default: terms not yet ended)")
        parser.add_argument("--section", default=None, help="One section, course code-section code (e.g. CSE2010-01)")
        parser.add_argument("--dry-run", action="store_true", help="Log what would be sent")

    def handle(self, *args: Any, **options: Any) -> int:
        platform = LmsPlatform.objects.filter(code=options["platform"]).first()
        if platform is None:
            self.error("Unknown platform code.")
            return self.FAILURE

        term = None
        if options.get("term"):
            term = Term.objects.filter(code=options["term"]).first()
            if term is None:
                self.error("Unknown term code.")
                return self.FAILURE

        sections = current_sections(term)
        if options.get("section"):
            course_code, _dash, section_code = str(options["section"]).partition("-")
            sections = sections.filter(course__code=course_code)
            if section_code:
                sections = sections.filter(section_code=section_code)

        sync = SyncSection()
        dry_run = self.is_dry_run()
        summary = {"sections": 0, "members": 0, "failed": 0}
        for section in list(sections.order_by("pk")):
            try:
                result = sync.handle(platform, section, dry_run)
            except Exception as error:
                summary["failed"] += 1
                self.warn(f"{section.label()}: {error}")
                continue
            summary["sections"] += 1
            summary["members"] += result["members"]

        self.record_result({"platform": platform.code, **summary})
        prefix = "Dry run: " if dry_run else ""
        self.info(
            f"{prefix}{summary['sections']} section(s), {summary['members']} member(s), {summary['failed']} failed."
        )
        return self.SUCCESS if summary["failed"] == 0 else self.PROBLEMS_FOUND
