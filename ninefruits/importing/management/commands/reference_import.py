"""Import reference data from a CSV file (original ``reference:import``).

Large reference data files. Uses the same resources and queued chunks as the admin screen, so
validation, matching by code and failed row reports are identical."""

from __future__ import annotations

import json
import os
from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.importing import registry
from ninefruits.importing.services import DEFAULT_CHUNK_SIZE, check_header, read_csv, start_import


class Command(AuditedCommand):
    help = "Import reference data from a CSV file (queued, same importers as the admin screen). Requires --actor."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "type", help="org_units, programs, buildings, rooms or lookup_values (later phases add more)"
        )
        parser.add_argument("file", help="CSV file with a header row (UTF-8)")
        parser.add_argument("--chunk", type=int, default=DEFAULT_CHUNK_SIZE, help="Rows per queued task")
        parser.add_argument("--dry-run", action="store_true", help="Check the header and count rows without importing")

    def handle(self, *args: Any, **options: Any) -> int:
        type_key = str(options["type"])
        resource = registry.resource_for(type_key)
        if resource is None:
            self.error(f"Unknown type. Use one of: {', '.join(registry.types())}.")
            return self.FAILURE

        path = str(options["file"])
        if not os.path.isfile(path) or not os.access(path, os.R_OK):
            self.error(f"Cannot read [{path}].")
            return self.FAILURE

        actor = self.actor()
        if actor is None:
            self.error("--actor is required: the import is recorded under that account and its result is shown there.")
            return self.FAILURE

        try:
            csv_file = read_csv(path)
        except UnicodeDecodeError:
            self.error("The file is not UTF-8 text.")
            return self.FAILURE
        header = check_header(resource, csv_file.headers)
        for column in header.unknown:
            self.warn(f"Ignored column [{column}].")
        if header.missing:
            self.error(f"Missing required columns: {', '.join(header.missing)}.")
            return self.FAILURE

        self.record_result({"type": type_key, "file": os.path.basename(path), "rows": len(csv_file.rows)})
        if self.is_dry_run():
            self.info(f"Dry run: {len(csv_file.rows)} row(s) with a valid header.")
            return self.SUCCESS

        import_run = start_import(
            type_key,
            actor,
            os.path.basename(path),
            os.path.realpath(path),
            csv_file.rows,
            chunk_size=max(1, int(options["chunk"])),
        )
        failed = import_run.failed_rows_count()
        self.record_result({"import_id": import_run.pk, "failed_rows": failed})

        if import_run.completed_at is not None:
            self.info(f"{import_run.successful_rows} imported, {failed} failed.")
            for row in import_run.failed_rows.order_by("id")[:20]:
                data = json.dumps(row.data, ensure_ascii=False)
                self.stdout.write(f"  {self.style.ERROR('failed')} {data} {row.validation_error}")
            return self.PROBLEMS_FOUND if failed else self.SUCCESS

        self.info(
            f"Queued import #{import_run.pk} ({import_run.total_rows} rows). "
            f"The result is shown to {actor.email} under CSV imports in the admin panel."
        )
        return self.SUCCESS
