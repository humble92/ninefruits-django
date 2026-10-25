"""Running CSV imports (original Filament ``ImportAction`` + ``ImportCsv`` jobs).

``start_import`` records the run (``imports``) and dispatches one Celery task per chunk of
rows; each chunk is imported by the type's resource and failed rows are kept in
``failed_import_rows`` with the reason. Small files from the admin screen are imported in the
request (``IMPORT_SYNC_MAX_ROWS``); large files and the command use the queue."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import IO, Any

import tablib
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from ninefruits.importing import registry
from ninefruits.importing.models import FailedImportRow, Import
from ninefruits.importing.resources import ReferenceResource, row_error_message

DEFAULT_CHUNK_SIZE = 100


@dataclass(frozen=True)
class CsvFile:
    headers: list[str]
    rows: list[dict[str, str]]


@dataclass(frozen=True)
class HeaderCheck:
    missing: list[str]
    unknown: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.missing


def read_csv(source: str | bytes | IO[bytes]) -> CsvFile:
    """A CSV file with a header row (UTF-8, a byte order mark is ignored)."""
    if isinstance(source, str):
        with open(source, "rb") as handle:
            data = handle.read()
    elif isinstance(source, bytes):
        data = source
    else:
        data = source.read()
    text = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    try:
        headers = [header.strip() for header in next(reader)]
    except StopIteration:
        return CsvFile([], [])
    rows = []
    for values in reader:
        if not any(value.strip() for value in values):
            continue
        rows.append({header: (values[index] if index < len(values) else "") for index, header in enumerate(headers)})
    return CsvFile(headers, rows)


def check_header(resource: type[ReferenceResource], headers: Sequence[str]) -> HeaderCheck:
    mapping = resource.normalize_headers(headers)
    mapped = set(mapping.values())
    return HeaderCheck(
        missing=[name for name in resource.required_columns() if name not in mapped],
        unknown=[header for header in headers if header not in mapping],
    )


def start_import(
    type_key: str,
    user: Any,
    file_name: str,
    file_path: str,
    rows: Sequence[Mapping[str, str]],
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    queue: bool = True,
) -> Import:
    """Records the run and imports the rows, through the queue (``queue=True``) or right now."""
    if registry.resource_for(type_key) is None:
        raise ValueError(f"Unknown import type {type_key!r}.")
    import_run = Import.objects.create(
        file_name=file_name[:255],
        file_path=file_path[:255],
        importer=type_key,
        total_rows=len(rows),
        user=user,
    )
    if not rows:
        Import.objects.filter(pk=import_run.pk).update(completed_at=timezone.now().replace(microsecond=0))
        import_run.refresh_from_db()
        return import_run
    chunks = [list(rows[start : start + max(1, chunk_size)]) for start in range(0, len(rows), max(1, chunk_size))]
    if queue:
        from ninefruits.importing.tasks import import_chunk

        def dispatch() -> None:
            for chunk in chunks:
                import_chunk.delay(import_run.pk, [dict(row) for row in chunk])

        # Workers must see the committed run; eager tasks (tests, CELERY_TASK_ALWAYS_EAGER) share
        # this connection and run right away.
        if transaction.get_connection().in_atomic_block and not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            transaction.on_commit(dispatch)
        else:
            dispatch()
    else:
        for chunk in chunks:
            import_rows(import_run.pk, chunk)
    import_run.refresh_from_db()
    return import_run


def import_rows(import_id: int, rows: Iterable[Mapping[str, str]]) -> tuple[int, int]:
    """Imports one chunk. Returns (imported, failed)."""
    import_run = Import.objects.get(pk=import_id)
    resource_class = registry.resource_for(import_run.importer)
    if resource_class is None:
        raise ValueError(f"Unknown import type {import_run.importer!r}.")
    rows = list(rows)
    headers = list(dict.fromkeys(header for row in rows for header in row))
    mapping = resource_class.normalize_headers(headers)
    columns = list(dict.fromkeys(mapping.values()))
    dataset = tablib.Dataset(headers=columns)
    for row in rows:
        mapped = {mapping[header]: value for header, value in row.items() if header in mapping}
        dataset.append([mapped.get(column, "") for column in columns])

    resource = resource_class()
    result = resource.import_data(dataset, dry_run=False, raise_errors=False, use_transactions=False)

    failures: dict[int, str] = {}
    for invalid in result.invalid_rows:
        failures[invalid.number] = row_error_message(invalid.error)
    for number, errors in result.row_errors():
        failures[number] = row_error_message(errors[0].error)
    for error in result.base_errors:
        # An error outside the rows (before/after import) fails the whole chunk.
        for number in range(1, len(rows) + 1):
            failures.setdefault(number, row_error_message(error.error))

    FailedImportRow.objects.bulk_create(
        [
            FailedImportRow(import_run=import_run, data=dict(rows[number - 1]), validation_error=message)
            for number, message in sorted(failures.items())
        ]
    )
    imported = len(rows) - len(failures)
    Import.objects.filter(pk=import_id).update(
        processed_rows=F("processed_rows") + len(rows), successful_rows=F("successful_rows") + imported
    )
    Import.objects.filter(pk=import_id, completed_at__isnull=True, processed_rows__gte=F("total_rows")).update(
        completed_at=timezone.now().replace(microsecond=0)
    )
    return imported, len(failures)


def failed_rows_csv(import_run: Import) -> str:
    """The failed rows with their reason (original "download failed rows")."""
    rows = list(import_run.failed_rows.order_by("id"))
    headers = list(dict.fromkeys(key for row in rows for key in (row.data or {})))
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([*headers, "error"])
    for row in rows:
        data = row.data or {}
        writer.writerow([_csv_safe(data.get(header, "")) for header in headers] + [_csv_safe(row.validation_error)])
    return buffer.getvalue()


def _csv_safe(value: Any) -> str:
    """Spreadsheet formula guard for cells that can only be formulas (``-`` stays: negative
    numbers and codes are re-imported from this file)."""
    text = "" if value is None else str(value)
    return f"'{text}" if text[:1] in ("=", "+", "@") else text


def sync_max_rows() -> int:
    return int(getattr(settings, "IMPORT_SYNC_MAX_ROWS", 500))
