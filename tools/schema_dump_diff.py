"""Compares a ``pg_dump --schema-only`` of a Django database with the original's dump.

The catalog fingerprint (``tests/db/test_schema_equivalence.py``) is the gate; this is the
porting plan's full ``pg_dump`` comparison (Phase 13). Each dump is split into its objects
(the ``-- Name: ...; Type: ...; Schema: ...`` headers) and the object bodies are compared.

Expected differences, reported as a summary and not as failures:

- objects of framework tables Django adds (``django_*``, ``auth_*``, allauth ``account_*``,
  ``socialaccount_*``, ``mfa_*``, ``knox_*``),
- the original's Laravel ``migrations`` table (Django keeps ``django_migrations``).

Usage::

    pg_dump --schema-only --no-owner --no-privileges <db> > /tmp/django-schema.sql
    uv run python tools/schema_dump_diff.py /tmp/django-schema.sql \\
        [porting/reference/laravel-schema.sql]

Exit code 0 when only expected differences remain, 1 otherwise.
"""

from __future__ import annotations

import difflib
import re
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "porting" / "reference" / "laravel-schema.sql"

HEADER = re.compile(r"^-- Name: (?P<name>.*?); Type: (?P<type>.*?); Schema: (?P<schema>.*?); Owner: .*$")
FRAMEWORK_TABLE = re.compile(r"\b(?:public\.)?(?:django_|auth_|account_|socialaccount_|mfa_|knox_)\w*")
# allauth indexes whose names do not carry the table prefix.
FRAMEWORK_NAMES = {"unique_authenticator_type", "unique_primary_email", "unique_verified_email"}
LARAVEL_ONLY = re.compile(r"\bmigrations(?:_id_seq|_pkey)?\b")
# Lines that differ between pg_dump runs (version banner, psql restrict keys).
VOLATILE = re.compile(r"^(?:-- Dumped (?:from|by) |\\restrict |\\unrestrict )")

Objects = dict[str, str]


def parse(text: str) -> Objects:
    objects: Objects = {}
    key: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if VOLATILE.match(line):
            continue
        match = HEADER.match(line)
        if match:
            if key is not None:
                objects[key] = _normalize(body)
            key = f"{match['type']} {match['schema']}.{match['name']}"
            body = []
        elif key is not None:
            body.append(line)
    if key is not None:
        objects[key] = _normalize(body)
    return objects


def _normalize(lines: Iterable[str]) -> str:
    kept = [line.rstrip() for line in lines if line.strip() and line.strip() != "--"]
    return "\n".join(kept)


def is_framework(key: str, body: str) -> bool:
    name = key.split(".", 1)[-1].split(" ", 1)[0]
    return name in FRAMEWORK_NAMES or bool(FRAMEWORK_TABLE.match(name)) or bool(FRAMEWORK_TABLE.search(body))


def is_laravel_only(key: str, body: str) -> bool:
    name = key.split(".", 1)[-1]
    return bool(LARAVEL_ONLY.fullmatch(name.split(" ", 1)[0])) or "public.migrations" in body


def compare(django: Objects, original: Objects) -> tuple[list[str], dict[str, int]]:
    problems: list[str] = []
    summary = {"compared": 0, "framework_added": 0, "laravel_only": 0}
    for key in sorted(original.keys() - django.keys()):
        if is_laravel_only(key, original[key]):
            summary["laravel_only"] += 1
        else:
            problems.append(f"missing in Django: {key}")
    for key in sorted(django.keys() - original.keys()):
        if is_framework(key, django[key]):
            summary["framework_added"] += 1
        else:
            problems.append(f"only in Django: {key}")
    for key in sorted(django.keys() & original.keys()):
        summary["compared"] += 1
        if django[key] != original[key]:
            diff = difflib.unified_diff(
                original[key].splitlines(), django[key].splitlines(), "original", "django", lineterm="", n=1
            )
            problems.append(f"differs: {key}\n" + "\n".join(diff))
    return problems, summary


def main(argv: list[str]) -> int:
    if not 1 <= len(argv) <= 2:
        print(__doc__)
        return 2
    django = parse(Path(argv[0]).read_text(encoding="utf-8"))
    original = parse(Path(argv[1] if len(argv) == 2 else REFERENCE).read_text(encoding="utf-8"))
    problems, summary = compare(django, original)
    for problem in problems:
        print(problem)
    identical = summary["compared"] - sum(problem.startswith("differs") for problem in problems)
    print(
        f"objects compared: {summary['compared']}, identical: {identical}, "
        f"framework objects added: {summary['framework_added']}, Laravel-only objects: {summary['laravel_only']}, "
        f"problems: {len(problems)}"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
