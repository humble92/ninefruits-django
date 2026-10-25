"""Synchronize the permissions table with the permission catalog in code. Original
``security:sync-permissions``."""

from __future__ import annotations

import sys
from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.security.actions import SyncPermissionCatalog


class Command(AuditedCommand):
    help = "Synchronize the permissions table with the permission catalog in code"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Show the changes without applying them")
        parser.add_argument(
            "--force", action="store_true", help="Delete permissions removed from the catalog without asking"
        )

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        sync = SyncPermissionCatalog()
        plan = sync.plan()
        for name in plan["created"]:
            self.stdout.write(f"  {self.style.SUCCESS('create')} {name}")
        for name in plan["deleted"]:
            self.stdout.write(f"  {self.style.ERROR('delete')} {name} (removed from every role)")
        self.record_result({"created": plan["created"], "deleted": plan["deleted"]})

        if self.is_dry_run():
            self.info(f"Dry run: {len(plan['created'])} to create, {len(plan['deleted'])} to delete.")
            return self.SUCCESS

        if plan["deleted"] and not options["force"] and not self._confirm(len(plan["deleted"])):
            self.warn("Cancelled. Nothing was changed.")
            return self.FAILURE

        result = sync()
        self.info(f"Permissions created: {len(result['created'])}, deleted: {len(result['deleted'])}")
        return self.SUCCESS

    @staticmethod
    def _confirm(count: int) -> bool:
        if not sys.stdin.isatty():
            return False
        import questionary

        return bool(questionary.confirm(f"Delete {count} permission(s) no longer in the catalog?", default=False).ask())
