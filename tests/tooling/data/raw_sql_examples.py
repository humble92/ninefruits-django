# ruff: noqa
# Example code for tests/tooling/test_raw_sql_check.py (original tests/PHPStan/data/raw-sql.php).
# Line numbers are asserted by the test: add new cases at the end.
from django.db import connection, migrations
from django.db.models.expressions import RawSQL
from psycopg import sql

from ninefruits.core.db import SqlFile

ALLOWED_ORDER = {"name": "name", "newest": "created_at DESC"}


def raw_sql_examples(user_input: str, user_id: int, order: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", [user_id])
        cursor.execute("SELECT set_config('app.locale', %s, false)", [user_input])
        RawSQL("lower(email) = %s", [user_input])
        statement = "SELECT 1"
        cursor.execute(statement)
        cursor.execute(SqlFile.read("sql/functions/i18n.sql"))
        cursor.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(user_input)))
        cursor.execute("SELECT * FROM users ORDER BY " + ALLOWED_ORDER["name"])
        migrations.RunSQL(SqlFile.read("sql/views/example.sql"))

        cursor.execute(f"SELECT * FROM users WHERE email = '{user_input}'")
        cursor.execute("SELECT * FROM users WHERE email = '%s'" % user_input)
        cursor.execute("SELECT * FROM users WHERE email = '{}'".format(user_input))
        cursor.execute("SELECT * FROM users WHERE email = " + user_input)
        cursor.execute(user_input)
        connection.cursor().execute(order)
        RawSQL(f"lower({user_input})", [])
        User.objects.raw("SELECT * FROM users WHERE name = '" + user_input + "'")
        User.objects.extra(where=["id = 1"])
        query = "SELECT * FROM users WHERE id = " + str(user_id)
        cursor.executemany(query, [])
        cursor.execute(user_input)  # raw-sql: ok (input comes from the ALLOWED_ORDER allow list)
        cursor.execute(user_input)  # raw-sql: ok

        User.objects.filter(name=user_input).update(name=user_input)
        cursor.execute("SELECT * FROM users WHERE id = %s", [f"{user_id}"])
