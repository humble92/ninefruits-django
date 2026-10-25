"""``media_prune_orphans`` (original ``media:prune-orphans``): removes media rows whose owner no
longer exists and directories on the media storage that no row refers to."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.media.services import prune_orphans


class Command(AuditedCommand):
    help = "Remove media rows whose owner no longer exists and files on the media storage that no row refers to"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="List only")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        dry_run = self.is_dry_run()
        summary = prune_orphans(dry_run=dry_run)
        for row in summary.orphan_rows:
            self.detail(row, "orphan" if dry_run else "deleted")
        for directory in summary.orphan_directories:
            self.detail(f"directory {directory}", "no media row" if dry_run else "deleted")
        self.record_result({"rows": summary.rows, "directories": summary.directories})
        prefix = "Dry run: " if dry_run else ""
        self.info(f"{prefix}{summary.rows} orphan row(s), {summary.directories} orphan director(ies).")
        return self.SUCCESS
