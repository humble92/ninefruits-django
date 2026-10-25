"""Expires stale drafts (original ``admission:expire-drafts``, ``ExpireDraftApplications``)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.admission.actions import ExpireDraftApplications
from ninefruits.core.commands import AuditedCommand


class Command(AuditedCommand):
    help = "Expire draft applications of closed cycles or untouched for the configured days (scheduled daily)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Count the drafts without changing them")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        expire = ExpireDraftApplications()
        if self.is_dry_run():
            count = expire.query().count()
            self.record_result({"drafts": count})
            self.info(f"Dry run: {count} draft(s) would expire.")
            return self.SUCCESS
        count = expire.handle()
        self.record_result({"expired": count})
        self.info(f"{count} draft(s) expired.")
        return self.SUCCESS
