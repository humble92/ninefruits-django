"""Background CSV imports (original Filament ``ImportCsv`` job)."""

from __future__ import annotations

from typing import Any

from celery import shared_task

from ninefruits.core.tasks import SystemTask


@shared_task(name="importing.import_chunk", base=SystemTask, bind=True)
def import_chunk(self: Any, import_id: int, rows: list[dict[str, str]]) -> dict[str, int]:
    """Imports one chunk of an import run; the run is completed when every row is processed."""
    from ninefruits.importing.services import import_rows

    imported, failed = import_rows(import_id, rows)
    return {"imported": imported, "failed": failed}
