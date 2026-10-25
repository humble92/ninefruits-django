"""Schema fingerprint for the equality check with the original Laravel schema (porting-plan 2.3,
13.5 item 6). Reads the PostgreSQL catalogs instead of parsing ``pg_dump`` output, so it needs
no client binary of the server's version. Django's own tables are left out (ADR 0001-django)."""

from __future__ import annotations

from collections.abc import Iterable

SCHEMAS = ("public", "audit", "reporting", "util")

# Framework tables that exist only on one side.
DJANGO_ONLY_PREFIXES = (
    "django_",
    "auth_",
    "account_",
    "mfa_",
    "socialaccount_",
    "knox_",
)
LARAVEL_ONLY_TABLES = ("migrations", "migrations_id_seq")

_QUERIES: dict[str, str] = {
    "column": """
        SELECT n.nspname || '.' || c.relname || '.' || a.attname || ' ' || format_type(a.atttypid, a.atttypmod)
               || CASE WHEN a.attnotnull THEN ' not null' ELSE '' END
               || COALESCE(' default ' || pg_get_expr(d.adbin, d.adrelid), '')
               || CASE WHEN a.attgenerated = 's' THEN ' generated stored' ELSE '' END
               || CASE WHEN a.attidentity <> '' THEN ' identity ' || a.attidentity::text ELSE '' END,
               c.relname
        FROM pg_attribute a
        JOIN pg_class c ON c.oid = a.attrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE a.attnum > 0 AND NOT a.attisdropped AND c.relkind IN ('r', 'p', 'v', 'm')
          AND n.nspname = ANY(%s)
    """,
    "relation": """
        SELECT n.nspname || '.' || c.relname || ' kind=' || c.relkind::text
               || ' rls=' || c.relrowsecurity::text || ' force_rls=' || c.relforcerowsecurity::text, c.relname
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r', 'p', 'v', 'm', 'S') AND n.nspname = ANY(%s)
    """,
    "constraint": """
        SELECT n.nspname || '.' || c.relname || ' ' || con.conname || ' ' || pg_get_constraintdef(con.oid), c.relname
        FROM pg_constraint con
        JOIN pg_class c ON c.oid = con.conrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = ANY(%s)
    """,
    "index": """
        SELECT pg_get_indexdef(i.indexrelid), c.relname
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = ANY(%s)
    """,
    "trigger": """
        SELECT pg_get_triggerdef(t.oid) || ' enabled=' || t.tgenabled::text, c.relname
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE NOT t.tgisinternal AND n.nspname = ANY(%s)
    """,
    "policy": """
        SELECT schemaname || '.' || tablename || ' ' || policyname || ' ' || permissive || ' ' || cmd
               || ' roles=' || array_to_string(roles, ',') || ' using=' || COALESCE(qual, '')
               || ' check=' || COALESCE(with_check, ''), tablename::text
        FROM pg_policies WHERE schemaname = ANY(%s)
    """,
    "function": """
        SELECT pg_get_functiondef(p.oid), ''
        FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = ANY(%s) AND p.prokind IN ('f', 'p')
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.objid = p.oid AND d.deptype = 'e')
    """,
    "view": """
        SELECT n.nspname || '.' || c.relname || ' ' || pg_get_viewdef(c.oid, true), c.relname
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('v', 'm') AND n.nspname = ANY(%s)
    """,
    "grant": """
        SELECT table_schema || '.' || table_name || ' ' || grantee || ' ' || privilege_type, table_name::text
        FROM information_schema.role_table_grants
        WHERE table_schema = ANY(%s) AND grantee IN ('app_runtime', 'app_reporting', 'PUBLIC')
    """,
    "routine_grant": """
        SELECT routine_schema || '.' || routine_name || ' ' || grantee || ' ' || privilege_type, ''
        FROM information_schema.role_routine_grants
        WHERE routine_schema = ANY(%s) AND grantee IN ('app_runtime', 'app_reporting')
    """,
    "default_acl": """
        SELECT n.nspname || ' ' || d.defaclobjtype::text || ' ' || array_to_string(d.defaclacl, ','), ''
        FROM pg_default_acl d JOIN pg_namespace n ON n.oid = d.defaclnamespace
        WHERE n.nspname = ANY(%s)
    """,
    "extension": """
        SELECT extname, '' FROM pg_extension WHERE extname <> 'plpgsql'
    """,
}


def _excluded(relation: str) -> bool:
    return (
        relation.startswith(DJANGO_ONLY_PREFIXES)
        or relation in LARAVEL_ONLY_TABLES
        or any(relation.startswith(prefix) and relation.endswith("_seq") for prefix in DJANGO_ONLY_PREFIXES)
    )


def fingerprint(cursor) -> list[str]:  # type: ignore[no-untyped-def]
    """Sorted lines describing every schema object. Equal lists mean equal schemas."""
    lines: list[str] = []
    for kind, sql in _QUERIES.items():
        cursor.execute(sql, [list(SCHEMAS)] if "%s" in sql else None)
        for text, relation in cursor.fetchall():
            if relation and _excluded(relation):
                continue
            for part in _normalize(text):
                lines.append(f"{kind}: {part}")
    return sorted(lines)


def _normalize(text: str) -> Iterable[str]:
    yield " ".join(text.split())


def diff(expected: list[str], actual: list[str]) -> list[str]:
    exp, act = set(expected), set(actual)
    return [f"- {line}" for line in sorted(exp - act)] + [f"+ {line}" for line in sorted(act - exp)]
