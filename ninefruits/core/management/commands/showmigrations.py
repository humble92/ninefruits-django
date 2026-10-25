from typing import Any

from django.core.management.commands.showmigrations import Command as ShowMigrationsCommand


class Command(ShowMigrationsCommand):
    def handle(self, *args: Any, **options: Any) -> None:
        if options.get("database") in (None, "default"):
            options["database"] = "migrator"
        super().handle(*args, **options)
