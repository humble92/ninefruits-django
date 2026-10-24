"""psycopg pool callbacks. Imported by settings, so this module must not import Django."""


def reset_connection(conn) -> None:  # type: ignore[no-untyped-def]
    """Runs when a connection returns to the pool: it never keeps the previous request's
    ``app.*`` settings (second line of defence after SetDatabaseSessionContextMiddleware)."""
    conn.execute("RESET ALL")
