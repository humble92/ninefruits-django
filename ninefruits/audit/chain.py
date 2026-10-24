"""Audit integrity services (original Phase 13 section 4: SealAuditChain, VerifyAuditChain,
PruneAudit; SQL in db/sql/triggers/audit_chain.sql).

- ``row_hash`` is set by an INSERT trigger on each audit table.
- :func:`seal` links unsealed rows in id order: ``chain_hash = sha256(previous || row_hash)``.
- :func:`verify` recomputes both; an edited, removed or inserted row shows up.
- :func:`prune` deletes sealed rows older than a date, in a transaction with
  ``app.audit_maintenance = on`` (the only exception to the append-only trigger).

Sealing and pruning need UPDATE/DELETE on the audit tables, so they run on the schema owner's
connection (``migrator``); verification only reads (``default``)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any

from django.db import connections, models, transaction
from django.utils import timezone

TABLES: tuple[str, ...] = ("record_changes", "activity_log", "security_events")
MAINTENANCE_DATABASE = "migrator"
READ_DATABASE = "default"

# Time column per table for the retention cut-off. (The original used created_at for
# security_events, which has no such column; occurred_at is its time column.)
TIME_COLUMNS: dict[str, str] = {
    "record_changes": "occurred_at",
    "activity_log": "created_at",
    "security_events": "occurred_at",
}


def tables(only: Iterable[str] | None = None) -> list[str]:
    """The audit tables in canonical order, limited to ``only`` when given (unknown names are
    ignored, like the original ``array_intersect``)."""
    selected = [name for name in (only or []) if name]
    return list(TABLES) if not selected else [name for name in TABLES if name in selected]


def model_for(table: str) -> type[models.Model]:
    from ninefruits.audit.models import ActivityLog, RecordChange, SecurityEvent

    return {"record_changes": RecordChange, "activity_log": ActivityLog, "security_events": SecurityEvent}[table]


def seal(table: str, *, using: str = MAINTENANCE_DATABASE) -> int:
    """Links the unsealed rows of ``audit.<table>`` to the chain. Returns how many."""
    _check(table)
    with connections[using].cursor() as cursor:
        cursor.execute("SELECT audit.seal(%s::regclass)", [f"audit.{table}"])
        return int(cursor.fetchone()[0])


@dataclass(frozen=True, slots=True)
class VerifyResult:
    table: str
    checked: int
    sealed: int
    row_mismatches: int
    chain_mismatches: int
    first_bad_id: int | None

    @property
    def problems(self) -> int:
        return self.row_mismatches + self.chain_mismatches

    def describe(self) -> str:
        text = (
            f"{self.checked} checked, {self.sealed} sealed, {self.row_mismatches} row mismatch(es), "
            f"{self.chain_mismatches} chain mismatch(es)"
        )
        return text + (f", first bad id {self.first_bad_id}" if self.first_bad_id else "")


def verify(table: str, *, using: str | None = None) -> VerifyResult:
    """Recomputes every row hash and the sealed chain of ``audit.<table>``."""
    _check(table)
    with connections[using or READ_DATABASE].cursor() as cursor:
        cursor.execute(
            "SELECT checked, sealed, row_mismatches, chain_mismatches, first_bad_id "
            "FROM audit.verify_chain(%s::regclass)",
            [f"audit.{table}"],
        )
        checked, sealed, row_mismatches, chain_mismatches, first_bad_id = cursor.fetchone()
    return VerifyResult(table, int(checked), int(sealed), int(row_mismatches), int(chain_mismatches), first_bad_id)


@dataclass(frozen=True, slots=True)
class PruneSummary:
    table: str
    before: str
    rows: int
    first_id: int | None
    last_id: int | None
    boundary_chain_hash: str | None
    unsealed: int

    def as_properties(self) -> dict[str, Any]:
        """Properties of the ``audit.pruned`` security event (original key order)."""
        return {
            "table": f"audit.{self.table}",
            "before": self.before,
            "rows": self.rows,
            "first_id": self.first_id,
            "last_id": self.last_id,
            "boundary_chain_hash": self.boundary_chain_hash,
        }


def _cutoff(before: date) -> datetime:
    return timezone.make_aware(datetime.combine(before, time.min))


def prune(table: str, before: date, *, dry_run: bool = False, using: str = MAINTENANCE_DATABASE) -> PruneSummary:
    """Deletes sealed rows of ``audit.<table>`` older than ``before`` (start of that day in the
    institution's time zone). Unsealed rows are kept (seal first). The summary keeps the id
    range and the chain hash at the boundary so the pruning can be reconciled with
    :func:`verify`."""
    _check(table)
    model = model_for(table)
    older = model._default_manager.using(using).filter(**{f"{TIME_COLUMNS[table]}__lt": _cutoff(before)})
    sealed = older.filter(chain_hash__isnull=False)
    stats = sealed.aggregate(rows=models.Count("id"), first_id=models.Min("id"), last_id=models.Max("id"))
    rows = int(stats["rows"] or 0)
    boundary = (
        model._default_manager.using(using).filter(pk=stats["last_id"]).values_list("chain_hash", flat=True).first()
        if rows
        else None
    )
    summary = PruneSummary(
        table=table,
        before=before.isoformat(),
        rows=rows,
        first_id=stats["first_id"],
        last_id=stats["last_id"],
        boundary_chain_hash=boundary,
        unsealed=older.filter(chain_hash__isnull=True).count(),
    )
    if not dry_run and rows:
        with transaction.atomic(using=using):
            with connections[using].cursor() as cursor:
                cursor.execute("SELECT set_config('app.audit_maintenance', 'on', true)")
            sealed.delete()
    return summary


def _check(table: str) -> None:
    if table not in TABLES:
        raise ValueError(f"Unknown audit table [{table}].")
