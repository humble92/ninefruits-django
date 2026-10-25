"""Audit hash chain (original Phase 13 section 4, tests/Feature/Tooling/OperationsCommandsTest.php
audit cases): rows are hashed at insert, ``audit_seal`` links them, ``audit_verify_chain``
detects tampering (exit code 2) and ``audit_prune`` deletes only sealed rows past a date and
records ``audit.pruned``.

Rows are written on the schema owner's connection inside the test transaction, so the services
run there too (``READ_DATABASE`` points the verification at it)."""

from __future__ import annotations

from datetime import date, timedelta
from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.db import connections
from django.utils import timezone

from ninefruits.audit import chain
from ninefruits.audit.models import ActivityLog, SecurityEvent
from ninefruits.audit.security_events import SecurityEventType
from tests.audit.support import database_error, make_user

pytestmark = pytest.mark.django_db(databases=["default", "migrator"])

OWNER = "migrator"


@pytest.fixture(autouse=True)
def _verify_on_the_owner_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chain, "READ_DATABASE", OWNER)


def audit_row(event: str, created_at: Any = None) -> int:
    created_at = created_at or timezone.now()
    with connections[OWNER].cursor() as cursor:
        cursor.execute(
            "INSERT INTO audit.activity_log (log_name, description, event, created_at, updated_at) "
            "VALUES ('test', %s, %s, %s, %s) RETURNING id",
            [event, event, created_at, created_at],
        )
        return int(cursor.fetchone()[0])


def maintenance(sql: str, params: list[Any]) -> None:
    with connections[OWNER].cursor() as cursor:
        cursor.execute("SELECT set_config('app.audit_maintenance', 'on', true)")
        cursor.execute(sql, params)


def run(command: str, *args: str, **options: Any) -> tuple[int, str]:
    out, err = StringIO(), StringIO()
    code = call_command(command, *args, stdout=out, stderr=err, **options)
    return code, out.getvalue() + err.getvalue()


def test_hashes_audit_rows_at_insert_seals_the_chain_and_detects_tampering() -> None:
    first = audit_row("test.first")
    second = audit_row("test.second")
    rows = ActivityLog.objects.using(OWNER).filter(log_name="test")
    assert rows.filter(row_hash__isnull=True).count() == 0

    code, output = run("audit_seal", table=["activity_log"])
    assert code == 0 and "row(s) sealed" in output
    assert len(rows.get(pk=first).chain_hash) == 64
    assert chain.verify("activity_log").problems == 0
    code, output = run("audit_verify_chain", table=["activity_log"])
    assert code == 0 and "Audit chain intact." in output

    # The runtime role cannot change audit rows; the owner in maintenance mode can, and the
    # chain shows it.
    assert database_error(lambda: ActivityLog.objects.filter(pk=first).update(reason="edited")) is not None
    maintenance("UPDATE audit.activity_log SET reason = 'edited' WHERE id = %s", [first])
    code, output = run("audit_verify_chain", table=["activity_log"])
    assert code == 2 and "1 row mismatch(es)" in output and f"first bad id {first}" in output

    maintenance("DELETE FROM audit.activity_log WHERE id = %s", [second])
    code, output = run("audit_verify_chain", table=["activity_log"])
    assert code == 2 and "chain mismatch(es)" in output


def test_detects_a_removed_row_inside_the_sealed_chain() -> None:
    ids = [audit_row(f"test.row{n}") for n in range(3)]
    chain.seal("activity_log")

    maintenance("DELETE FROM audit.activity_log WHERE id = %s", [ids[1]])

    result = chain.verify("activity_log")
    assert result.chain_mismatches >= 1 and result.first_bad_id == ids[2]
    code, output = run("audit_verify_chain", table=["activity_log"])
    assert code == 2 and "chain mismatch(es)" in output


def test_prunes_sealed_audit_rows_past_the_retention_date() -> None:
    old = audit_row("test.old", timezone.now() - timedelta(days=3 * 365))
    audit_row("test.new")
    before = (timezone.localdate() - timedelta(days=365)).isoformat()

    code, output = run("audit_prune", table=["activity_log"])
    assert code == 1 and "--before=YYYY-MM-DD is required." in output

    code, output = run("audit_prune", before=before, table=["activity_log"], dry_run=True)
    assert code == 0 and "would delete 0 row(s)" in output and "unsealed row(s) kept" in output

    run("audit_seal", table=["activity_log"])
    code, output = run("audit_prune", before=before, table=["activity_log"], dry_run=True)
    assert "would delete 1 row(s)" in output
    assert ActivityLog.objects.using(OWNER).filter(pk=old).exists()

    admin = make_user("ops@example.test")
    code, output = run("audit_prune", before=before, table=["activity_log"], actor="ops@example.test")
    assert code == 0 and f"deleted 1 row(s) (ids {old}–{old})" in output

    assert not ActivityLog.objects.using(OWNER).filter(pk=old).exists()
    assert ActivityLog.objects.using(OWNER).filter(event="test.new").exists()
    assert chain.verify("activity_log").problems == 0

    event = SecurityEvent.objects.filter(type=SecurityEventType.AUDIT_PRUNED).get()
    assert event.user_id == admin.pk
    assert event.properties["table"] == "audit.activity_log"
    assert (event.properties["rows"], event.properties["first_id"], event.properties["last_id"]) == (1, old, old)
    assert event.properties["before"] == before
    assert len(event.properties["boundary_chain_hash"]) == 64

    run_record = ActivityLog.objects.filter(log_name="command", properties__command="audit_prune").latest("id")
    assert run_record.properties["result"]["activity_log"]["rows"] == 1


def test_prunes_security_events_by_their_time_column() -> None:
    summary = chain.prune("security_events", date.today(), dry_run=True)
    assert summary.table == "security_events" and summary.rows >= 0


def test_selects_tables_in_canonical_order() -> None:
    assert chain.tables([]) == ["record_changes", "activity_log", "security_events"]
    assert chain.tables(["security_events", "unknown", "activity_log"]) == ["activity_log", "security_events"]
    with pytest.raises(ValueError):
        chain.seal("users")
