"""``createsuperuser`` is disabled (porting-plan 13.2): a Django superuser would bypass the
permission catalog, role assignments and the audit trail. The first administrator is created
with ``security_create_administrator``."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser


class Command(BaseCommand):
    help = "Disabled. Create the first administrator with security_create_administrator."

    def add_arguments(self, parser: CommandParser) -> None:
        # Accept (and ignore) Django's options so scripts get the explanation, not a usage error.
        parser.add_argument("--username", "--email", dest="identifier")
        parser.add_argument("--noinput", "--no-input", action="store_false", dest="interactive")
        parser.add_argument("--database")

    def handle(self, *args: Any, **options: Any) -> None:
        raise CommandError(
            "createsuperuser is disabled in Ninefruits. Create the first administrator with "
            "`uv run manage.py security_create_administrator` (see docs/manual/en/operations/commands.md)."
        )
