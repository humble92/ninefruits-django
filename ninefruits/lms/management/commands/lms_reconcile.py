"""Compares the rosters on an LMS platform with the academic system and fixes the differences
(original ``lms:reconcile``; scheduled daily at 02:30 as the Celery beat task ``lms.reconcile``)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.lms.actions import ReconcilePlatform
from ninefruits.lms.models import LmsPlatform
from ninefruits.term.models import Term


class Command(AuditedCommand):
    help = "Compare the rosters on an LMS platform with the academic system and fix the differences (nightly)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("platform", nargs="?", default=None, help="Platform code (default: every active platform)")
        parser.add_argument("--term", default=None, help="Term code")
        parser.add_argument("--dry-run", action="store_true", help="Report differences only")

    def handle(self, *args: Any, **options: Any) -> int:
        code = options.get("platform")
        platforms = list(
            LmsPlatform.objects.filter(code=code) if code else LmsPlatform.objects.active().order_by("code")
        )
        if not platforms:
            self.error("Unknown platform code." if code else "No active platform.")
            return self.FAILURE

        term = None
        if options.get("term"):
            term = Term.objects.filter(code=options["term"]).first()
            if term is None:
                self.error("Unknown term code.")
                return self.FAILURE

        reconcile = ReconcilePlatform()
        failed = 0
        for platform in platforms:
            summary = reconcile.handle(platform, term, self.is_dry_run())
            failed += summary["failed"]
            self.record_result({platform.code: dict(summary)})
            self.detail(
                platform.code,
                f"{summary['sections']} section(s): +{summary['added']} -{summary['removed']}, "
                f"{summary['failed']} failed",
            )
        return self.SUCCESS if failed == 0 else self.PROBLEMS_FOUND
