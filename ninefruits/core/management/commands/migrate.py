"""``migrate`` runs on the schema owner connection (``migrator``) unless ``--database`` is
given (porting-plan 5.3). The runtime role cannot run DDL."""

from typing import Any

from django.core.management.commands.migrate import Command as MigrateCommand


class Command(MigrateCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        if options.get("database") in (None, "default") and not options.get("_runtime", False):
            options["database"] = "migrator"
        super().handle(*args, **options)
