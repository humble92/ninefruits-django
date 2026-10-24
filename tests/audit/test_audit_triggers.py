"""Original tests/Database/Security/AuditTriggerTest.php: the data audit trigger
(``audit.record_change()``, ``util.enable_audit``) records changes made outside the ORM,
redacts secret columns, skips no-op updates and changes of ignored columns only, and the audit
tables cannot be modified even by their owner."""

from __future__ import annotations

from typing import Any

import pytest
from django.db import DatabaseError, connection, connections, transaction

from ninefruits.audit.models import RecordChange
from ninefruits.core.db import session_context
from tests.audit.support import database_error, make_user, scalar

pytestmark = pytest.mark.django_db(databases=["default", "migrator"])


def latest_record_change(table: str, using: str = "default") -> RecordChange:
    return RecordChange.objects.using(using).filter(table_name=table).latest("id")


def test_records_inserts_updates_and_deletes_with_the_request_context() -> None:
    session_context().for_user(42, "request-1")

    user = make_user(name="Before")
    user.name = "After"
    user.save()

    change = latest_record_change("users")
    assert change.operation == "UPDATE"
    assert change.record_id == str(user.pk)
    assert "name" in change.changed_columns
    assert change.old_values["name"] == "Before"
    assert change.new_values["name"] == "After"
    assert change.user_id == 42
    assert change.actor == "user:42"
    assert change.request_id == "request-1"
    assert change.database_user == "app_runtime"
    assert change.transaction_id > 0

    user.delete()

    assert latest_record_change("users").operation == "DELETE"


@pytest.mark.usefixtures("without_baseline")
def test_records_changes_made_outside_the_application() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", ["Direct", "direct@example.test", "x"]
        )

    change = latest_record_change("users")
    assert change.operation == "INSERT"
    assert change.actor is None
    assert change.new_values["email"] == "direct@example.test"


def test_redacts_secret_columns() -> None:
    user = make_user()
    with connection.cursor() as cursor:
        cursor.execute("UPDATE users SET remember_token = %s WHERE id = %s", ["remember-me", user.pk])

    insert = RecordChange.objects.get(table_name="users", record_id=str(user.pk), operation="INSERT")
    update = latest_record_change("users")
    assert insert.new_values["password"] == "[redacted]"
    assert update.new_values["remember_token"] == "[redacted]"
    assert "remember_token" in update.changed_columns


def test_skips_updates_that_change_nothing() -> None:
    user = make_user()
    count = RecordChange.objects.count()

    with connection.cursor() as cursor:
        cursor.execute("UPDATE users SET name = %s WHERE id = %s", [user.name, user.pk])

    assert RecordChange.objects.count() == count


def _owner_execute(sql: str, params: list[Any] | None = None) -> None:
    with connections["migrator"].cursor() as cursor:
        cursor.execute(sql, params or [])


def test_skips_updates_that_change_only_ignored_columns() -> None:
    # A table of the test transaction on the owner connection, audited like sections
    # (util.enable_audit('sections', '{}', ARRAY['enrolled_count', 'updated_at'])).
    _owner_execute("CREATE TABLE audit_trigger_probe (id bigint PRIMARY KEY, title text, secret text, counter int)")
    _owner_execute("SELECT util.enable_audit('audit_trigger_probe', ARRAY['secret'], ARRAY['counter'])")
    _owner_execute("INSERT INTO audit_trigger_probe VALUES (1, 'a', 's1', 0)")
    count = RecordChange.objects.using("migrator").filter(table_name="audit_trigger_probe").count()

    _owner_execute("UPDATE audit_trigger_probe SET counter = counter + 1 WHERE id = 1")
    assert RecordChange.objects.using("migrator").filter(table_name="audit_trigger_probe").count() == count

    _owner_execute("UPDATE audit_trigger_probe SET counter = counter + 1, title = 'b' WHERE id = 1")
    change = latest_record_change("audit_trigger_probe", using="migrator")
    assert change.changed_columns == ["counter", "title"]
    assert change.old_values["secret"] == "[redacted]" and change.new_values["secret"] == "[redacted]"
    assert change.database_user == "app_migrator"

    _owner_execute("TRUNCATE audit_trigger_probe")
    truncate = latest_record_change("audit_trigger_probe", using="migrator")
    assert truncate.operation == "TRUNCATE" and truncate.record_id is None


def test_keeps_audit_records_append_only_for_the_application() -> None:
    make_user()

    assert "permission denied" in database_error(lambda: RecordChange.objects.all().delete())

    def forge() -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO audit.record_changes (table_schema, table_name, operation, database_user) "
                "VALUES ('public', 'users', 'INSERT', 'forged')"
            )

    assert "permission denied" in database_error(forge)


@pytest.mark.parametrize("table", ["security_events", "activity_log", "record_changes"])
def test_blocks_changes_to_audit_records_even_for_the_schema_owner(table: str) -> None:
    statements = {
        "security_events": "DELETE FROM audit.security_events",
        "activity_log": "UPDATE audit.activity_log SET reason = 'x'",
        "record_changes": "TRUNCATE audit.record_changes",
    }
    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic(using="migrator"):
        _owner_execute(statements[table])

    assert scalar("SELECT current_user", using="migrator") == "app_migrator"
