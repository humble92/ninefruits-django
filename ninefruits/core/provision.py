"""Database provisioning as a superuser: application roles and per-database preparation.
Python equivalent of ``db/sql/roles/create_roles.sql`` and ``prepare_database.sql`` (those use
psql ``\\gexec`` and remain the reference for operators). Used by test setup and setup scripts."""

from __future__ import annotations

from typing import Any

import psycopg
from django.conf import settings
from psycopg import sql


def superuser_connect(dbname: str = "postgres") -> psycopg.Connection[Any]:
    db = settings.DATABASES["default"]
    return psycopg.connect(
        host=db["HOST"],
        port=db["PORT"],
        dbname=dbname,
        user=settings.DB_SUPERUSER_USERNAME,
        password=settings.DB_SUPERUSER_PASSWORD,
        autocommit=True,
    )


def create_roles(conn: psycopg.Connection[Any], passwords: dict[str, str]) -> None:
    """``passwords``: role name -> password, for roles that do not exist yet."""
    for role, password in passwords.items():
        exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", [role]).fetchone()
        if not exists:
            conn.execute(
                sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(sql.Identifier(role), sql.Literal(password))
            )
        conn.execute(
            sql.SQL("ALTER ROLE {} NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB").format(sql.Identifier(role))
        )


def database_exists(conn: psycopg.Connection[Any], name: str) -> bool:
    return conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", [name]).fetchone() is not None


def drop_database(conn: psycopg.Connection[Any], name: str) -> None:
    conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


def create_database(conn: psycopg.Connection[Any], name: str) -> None:
    conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def prepare_database(name: str) -> None:
    """Same statements as db/sql/roles/prepare_database.sql."""
    migrator = settings.DATABASES["migrator"]["USER"]
    runtime = settings.DB_RUNTIME_ROLE
    reporting = settings.DB_REPORTING_ROLE
    db = sql.Identifier(name)
    with superuser_connect(name) as conn:
        conn.execute(sql.SQL("ALTER DATABASE {} OWNER TO {}").format(db, sql.Identifier(migrator)))
        conn.execute(sql.SQL("ALTER SCHEMA public OWNER TO {}").format(sql.Identifier(migrator)))
        conn.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
        conn.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(db))
        conn.execute(sql.SQL("GRANT CONNECT, TEMPORARY ON DATABASE {} TO {}").format(db, sql.Identifier(runtime)))
        conn.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(db, sql.Identifier(reporting)))
