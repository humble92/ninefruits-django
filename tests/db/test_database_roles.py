"""Original tests/Database/Foundation/DatabaseRolesTest.php."""

import pytest
from django.db import DatabaseError, connection, connections, transaction

pytestmark = pytest.mark.django_db(databases=["default", "migrator"])


def _scalar(sql: str, alias: str = "default") -> object:
    with connections[alias].cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchone()[0]


def test_connects_with_the_runtime_role_not_the_schema_owner() -> None:
    assert _scalar("SELECT current_user") == "app_runtime"
    assert _scalar("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user") is False


def test_creates_the_application_schemas() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT nspname FROM pg_namespace")
        schemas = {row[0] for row in cursor.fetchall()}
    assert {"audit", "reporting", "util"} <= schemas


def test_runtime_role_cannot_change_the_schema() -> None:
    with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE public.not_allowed (id int)")


def test_migrations_run_on_the_migrator_connection() -> None:
    assert _scalar("SELECT current_user", "migrator") == "app_migrator"
    assert _scalar("SELECT tableowner FROM pg_tables WHERE tablename = 'users'", "migrator") == "app_migrator"


def test_runtime_role_cannot_truncate() -> None:
    with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE users")
