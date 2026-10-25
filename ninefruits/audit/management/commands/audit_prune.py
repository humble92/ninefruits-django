"""``audit_prune`` (original ``audit:prune``): deletes audit rows past the retention period
(sealed rows only) on the schema owner's connection. Every deletion is itself recorded as the
security event ``audit.pruned`` (table, cut-off date, rows, id range, boundary chain hash)."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core.management.base import CommandParser

from ninefruits.audit import chain
from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.core.commands import AuditedCommand


class Command(AuditedCommand):
    help = "Delete audit rows past the retention period (sealed rows only), on the schema owner's connection"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--before", help="Delete rows older than this date (YYYY-MM-DD), required")
        parser.add_argument("--table", action="append", default=[], help="Only these audit tables")
        parser.add_argument("--dry-run", action="store_true", help="Count only")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        try:
            before = date.fromisoformat(options["before"]) if options["before"] else None
        except ValueError:
            before = None
        if before is None:
            self.error("--before=YYYY-MM-DD is required.")
            return self.FAILURE

        dry_run = self.is_dry_run()
        summary: dict[str, Any] = {"before": before.isoformat()}
        for table in chain.tables(options["table"]):
            result = chain.prune(table, before, dry_run=dry_run)
            summary[table] = {
                "rows": result.rows,
                "first_id": result.first_id,
                "last_id": result.last_id,
                "boundary_chain_hash": result.boundary_chain_hash,
            }
            if not dry_run and result.rows > 0:
                record_security_event(
                    SecurityEventType.AUDIT_PRUNED, user=self.actor(), properties=result.as_properties()
                )
            text = ("would delete " if dry_run else "deleted ") + f"{result.rows} row(s)"
            if result.rows > 0:
                text += f" (ids {result.first_id}–{result.last_id})"
            if result.unsealed > 0:
                text += f", {result.unsealed} unsealed row(s) kept (run audit_seal first)"
            self.detail(f"audit.{table}", text)

        self.record_result({"dry_run": dry_run, **summary})
        return self.SUCCESS
