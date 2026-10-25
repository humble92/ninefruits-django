"""``naming_check`` (original ``naming:check``, ``App\\Console\\Commands\\Naming\\CheckNaming``).

Checks names against docs/development/naming.md. The original read table and column names from
the Laravel migration sources; here the schema is replayed DDL, so the check reads the actual
database catalog instead, plus the Django specific names:

- tables and columns in the ``public``, ``audit`` and ``reporting`` schemas: snake_case, no
  forbidden suffix, no language code, ``timestamptz`` for points in time, boolean names
  (``is_``, ``has_``, ``can_`` or a verb), ``date`` columns ending in ``_date``;
- migration file names of the Ninefruits apps (``NNNN_snake_case.py``, no auto-generated
  dates);
- management command names of the Ninefruits apps (``context_action``);
- translation catalogs: msgids are English source text, not semantic keys
  (``registration.errors.credit_limit_exceeded``), and msgctxt values are snake_case groups.

Framework and package tables keep their upstream names (``UPSTREAM_TABLES``).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.management.base import CommandParser
from django.db import connections

from ninefruits.core.commands import StatusCommand

#: Tables defined by Django, packages and the original framework (Laravel cache, queue and
#: session tables, spatie settings/permission tables, Filament import tables, media library),
#: which keep their upstream names (original ``UPSTREAM_MIGRATIONS``).
UPSTREAM_TABLES = frozenset(
    {
        "cache",
        "cache_locks",
        "jobs",
        "job_batches",
        "failed_jobs",
        "settings",
        "features",
        "media",
    }
)
UPSTREAM_PREFIXES = (
    "django_",
    "auth_",
    "account_emailaddress",
    "account_emailconfirmation",
    "socialaccount_",
    "mfa_",
    "knox_",
)

SCHEMAS = ("public", "audit", "reporting")

#: Django commands that Ninefruits overrides under their Django names.
FRAMEWORK_COMMANDS = frozenset(
    {"migrate", "makemigrations", "showmigrations", "sqlmigrate", "flush", "createsuperuser"}
)

SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")
#: msgctxt: the original group, or the key's parent path when the group itself is ambiguous
#: (``registration.actions``, see tools/convert_translations.py).
CATALOG_CONTEXT = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
LANGUAGE_CODE = re.compile(r"(^|_)(ko|kr|kor|en|eng|cn|zh|chn|ja|jp|lo|lao)(_|$)")
FORBIDDEN_SUFFIX = re.compile(r"(_old|_new|_backup|_bak|_tmp|_temp|_copy|_\d{6,8}|\d+)$")
BOOLEAN_PREFIX = re.compile(r"^(is|has|can|should|counts|allows|requires|blocks)_")
MIGRATION_NAME = re.compile(r"^(?P<number>\d{4})_(?P<name>[a-z0-9_]+)\.py$")
AUTO_MIGRATION = re.compile(r"_auto_\d{8}_\d{4}$")
COMMAND_NAME = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")
SEMANTIC_KEY = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)+$")

TIMESTAMP_WITHOUT_TIME_ZONE = "timestamp without time zone"


def check_name(label: str, name: str) -> list[str]:
    problems = []
    if not SNAKE_CASE.match(name):
        problems.append(f"{label} is not snake_case")
    if FORBIDDEN_SUFFIX.search(name):
        problems.append(f"{label} has a forbidden suffix (_old, _new, _backup, _tmp, dates or numbers)")
    if LANGUAGE_CODE.search(name):
        problems.append(f"{label} contains a language code; store translations in one jsonb column")
    return problems


def is_upstream_table(table: str) -> bool:
    return table in UPSTREAM_TABLES or table.startswith(UPSTREAM_PREFIXES)


def check_columns(rows: Iterable[tuple[str, str, str, str]]) -> list[str]:
    """``rows``: (schema, table, column, data_type) from the catalog."""
    problems: list[str] = []
    tables: set[tuple[str, str]] = set()
    for schema, table, column, data_type in rows:
        if is_upstream_table(table):
            continue
        qualified = table if schema == "public" else f"{schema}.{table}"
        if (schema, table) not in tables:
            tables.add((schema, table))
            problems += check_name(f"table [{qualified}]", table)
        label = f"column [{qualified}.{column}]"
        problems += check_name(label, column)
        if data_type == TIMESTAMP_WITHOUT_TIME_ZONE:
            problems.append(f"{label} is timestamp without time zone; use timestamptz")
        if data_type == "boolean" and not BOOLEAN_PREFIX.match(column):
            problems.append(f"boolean {label} should start with is_, has_, can_ or a verb")
        if data_type == "date" and not column.endswith("_date"):
            problems.append(f"date {label} should end with _date")
    return list(dict.fromkeys(problems))


def check_migration_names(names: Iterable[str]) -> list[str]:
    problems: list[str] = []
    for file_name in names:
        if file_name == "__init__.py":
            continue
        match = MIGRATION_NAME.match(file_name)
        if match is None:
            problems.append(f"migration [{file_name}] should be NNNN_snake_case.py")
            continue
        name = match.group("name")
        if AUTO_MIGRATION.search(name) or name.startswith("auto_"):
            problems.append(f"migration [{file_name}] has an auto-generated name; name it after what it does")
            continue
        # Language names are fine here ("add_lao_locale"): only columns must not carry them.
        if not SNAKE_CASE.match(name):
            problems.append(f"migration [{file_name}] is not snake_case")
        if FORBIDDEN_SUFFIX.search(name):
            problems.append(
                f"migration [{file_name}] has a forbidden suffix (_old, _new, _backup, _tmp, dates or numbers)"
            )
    return problems


def check_command_names(names: Iterable[str]) -> list[str]:
    return [
        f"command [{name}] should be named context_action (original context:action)"
        for name in names
        if name not in FRAMEWORK_COMMANDS and not COMMAND_NAME.match(name)
    ]


def check_catalog_entries(entries: Iterable[tuple[str | None, str]], label: str) -> list[str]:
    """``entries``: (msgctxt, msgid)."""
    problems: list[str] = []
    for context, msgid in entries:
        if SEMANTIC_KEY.match(msgid):
            problems.append(f"{label}: msgid [{msgid}] looks like a translation key; use the English source text")
        if context is not None and not CATALOG_CONTEXT.match(context):
            problems.append(f"{label}: msgctxt [{context}] should be a snake_case group name")
    return problems


def _po_entries(path: Path) -> list[tuple[str | None, str]]:
    """msgctxt/msgid pairs of a .po file (single line and continued strings)."""
    entries: list[tuple[str | None, str]] = []
    context: str | None = None
    current: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal current, context
        if current == "msgid":
            text = "".join(buffer)
            if text:
                entries.append((context, text))
            context = None
        elif current == "msgctxt":
            context = "".join(buffer)
        current = None
        buffer.clear()

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#~"):
            continue
        keyword = stripped.split(" ", 1)[0]
        if keyword in {"msgctxt", "msgid", "msgid_plural", "msgstr"} or keyword.startswith("msgstr["):
            flush()
            if keyword in {"msgctxt", "msgid"}:
                current = keyword
                buffer.append(_unquote(stripped[len(keyword) :].strip()))
        elif stripped.startswith('"') and current is not None:
            buffer.append(_unquote(stripped))
        elif not stripped:
            flush()
    flush()
    return entries


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    return value.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")


def ninefruits_app_configs() -> list[Any]:
    return [config for config in apps.get_app_configs() if config.name.startswith("ninefruits.")]


class Command(StatusCommand):
    help = "Check database, migration, command and translation names against the naming conventions"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--database", default="default", help="Database connection to check (default: default).")
        parser.add_argument("--skip-database", action="store_true", help="Check files only.")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]
        problems: list[str] = []
        if not options["skip_database"]:
            problems += check_columns(self._catalog(options["database"]))
        problems += self._file_problems()

        for problem in problems:
            self.stdout.write(self.style.ERROR("✗ ") + problem)
        if not problems:
            self.stdout.write(self.style.SUCCESS("Names follow the conventions."))
            return 0
        self.stderr.write(f"{len(problems)} naming problem(s). See docs/development/naming.md.")
        return self.PROBLEMS_FOUND

    @staticmethod
    def _catalog(alias: str) -> list[tuple[str, str, str, str]]:
        with connections[alias].cursor() as cursor:
            cursor.execute(
                "SELECT c.table_schema, c.table_name, c.column_name, c.data_type"
                " FROM information_schema.columns c"
                " JOIN information_schema.tables t"
                " ON t.table_schema = c.table_schema AND t.table_name = c.table_name"
                " WHERE c.table_schema = ANY(%s)"
                " ORDER BY c.table_schema, c.table_name, c.ordinal_position",
                [list(SCHEMAS)],
            )
            return [tuple(row) for row in cursor.fetchall()]

    @staticmethod
    def _file_problems() -> list[str]:
        problems: list[str] = []
        for config in ninefruits_app_configs():
            root = Path(config.path)
            migrations = root / "migrations"
            if migrations.is_dir():
                problems += [
                    f"{config.label}: {problem}"
                    for problem in check_migration_names(sorted(p.name for p in migrations.glob("*.py")))
                ]
            commands = root / "management" / "commands"
            if commands.is_dir():
                names = sorted(p.stem for p in commands.glob("*.py") if not p.stem.startswith("_"))
                problems += [f"{config.label}: {problem}" for problem in check_command_names(names)]
            for po in sorted((root / "locale").glob("*/LC_MESSAGES/*.po")):
                problems += check_catalog_entries(_po_entries(po), str(po.relative_to(settings.BASE_DIR)))
        for locale_path in settings.LOCALE_PATHS:
            for po in sorted(Path(locale_path).glob("*/LC_MESSAGES/*.po")):
                problems += check_catalog_entries(_po_entries(po), str(po.relative_to(settings.BASE_DIR)))
        return problems
