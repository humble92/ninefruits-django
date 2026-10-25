"""``flush`` truncates as the schema owner: the runtime role has no TRUNCATE privilege. Used by
transactional tests. Cascades because tables without a Django model may reference flushed ones."""

from typing import Any

from django.core.management.commands.flush import Command as FlushCommand


class Command(FlushCommand):
    def handle(self, **options: Any) -> None:
        if options.get("database") in (None, "default"):
            options["database"] = "migrator"
        options["allow_cascade"] = True
        super().handle(**options)
