"""``audit_seal`` (original ``audit:seal``): links new audit rows into the hash chain. Scheduled
nightly at 03:30."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.audit import chain
from ninefruits.core.commands import AuditedCommand


class Command(AuditedCommand):
    help = "Link new audit rows into the tamper-evidence hash chain (nightly)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--table",
            action="append",
            default=[],
            help="Only these audit tables (record_changes, activity_log, security_events)",
        )

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        summary: dict[str, int] = {}
        for table in chain.tables(options["table"]):
            sealed = chain.seal(table)
            summary[table] = sealed
            self.detail(f"audit.{table}", f"{sealed} row(s) sealed")
        self.record_result(summary)
        return self.SUCCESS
