"""``audit_verify_chain`` (original ``audit:verify-chain``): recomputes every audit row hash and
the sealed chain. Read only, not audited. Exit code 2 when a row was changed, removed or
inserted out of order."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.audit import chain
from ninefruits.core.commands import StatusCommand


class Command(StatusCommand):
    help = (
        "Recompute every audit row hash and the sealed chain; exit 2 when a row was changed, "
        "removed or inserted out of order"
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--table", action="append", default=[], help="Only these audit tables")

    def handle(self, *args: Any, **options: Any) -> int:
        problems = 0
        for table in chain.tables(options["table"]):
            result = chain.verify(table)
            problems += result.problems
            self.detail(f"audit.{table}", result.describe())
        if problems > 0:
            self.error(f"{problems} problem(s) found: the audit tables were modified outside the application.")
            return self.PROBLEMS_FOUND
        self.info("Audit chain intact.")
        return self.SUCCESS
