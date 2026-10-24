"""``naming_check`` (original tests/Unit/Tooling/CheckNamingTest.php).

The original parsed migration sources; the Django command checks the database catalog, so the
cases are expressed as catalog rows (schema, table, column, data type)."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import call_command

from ninefruits.core.management.commands.naming_check import (
    check_catalog_entries,
    check_columns,
    check_command_names,
    check_migration_names,
)


def problems(*rows: tuple[str, str, str]) -> str:
    return "\n".join(check_columns(("public", table, column, data_type) for table, column, data_type in rows))


def test_accepts_names_that_follow_the_conventions() -> None:
    assert (
        problems(
            ("course_versions", "id", "bigint"),
            ("course_versions", "title", "jsonb"),
            ("course_versions", "counts_toward_credit_limit", "boolean"),
            ("course_versions", "is_retake", "boolean"),
            ("course_versions", "birth_date", "date"),
            ("course_versions", "finalized_at", "timestamp with time zone"),
            ("course_versions", "created_at", "timestamp with time zone"),
        )
        == ""
    )


@pytest.mark.parametrize(
    ("row", "expected"),
    [
        pytest.param(("people", "name_kr", "character varying"), "language code", id="language code column"),
        pytest.param(("people", "en_name", "character varying"), "language code", id="language prefix"),
        pytest.param(("scores_backup", "id", "bigint"), "forbidden suffix", id="backup table"),
        pytest.param(("scores_20170302", "id", "bigint"), "forbidden suffix", id="date suffix table"),
        pytest.param(("scores", "score2", "character varying"), "forbidden suffix", id="numbered column"),
        pytest.param(("sections", "SFOP_MAX", "integer"), "snake_case", id="upper case"),
        pytest.param(
            ("enrollments", "dropped_at", "timestamp without time zone"), "timestamptz", id="timestamp without zone"
        ),
        pytest.param(("enrollments", "retake", "boolean"), "boolean column", id="boolean without prefix"),
        pytest.param(("people", "birthday", "date"), "_date", id="date without suffix"),
    ],
)
def test_rejects_legacy_style_names(row: tuple[str, str, str], expected: str) -> None:
    assert expected in problems(row)


def test_upstream_tables_keep_their_names() -> None:
    assert (
        problems(("django_session", "expire_date", "timestamp with time zone"), ("settings", "locked", "boolean")) == ""
    )


def test_audit_and_reporting_tables_are_checked_with_their_schema() -> None:
    result = check_columns([("audit", "activity_log", "score2", "integer")])

    assert result == [
        "column [audit.activity_log.score2] has a forbidden suffix (_old, _new, _backup, _tmp, dates or numbers)"
    ]


def test_migration_file_names() -> None:
    assert check_migration_names(["__init__.py", "0001_initial.py", "0006_lao_locale.py"]) == []
    assert "auto-generated" in check_migration_names(["0002_auto_20261024_1200.py"])[0]
    assert "forbidden suffix" in check_migration_names(["0003_merge_20261024_1200.py"])[0]
    assert "NNNN_snake_case" in check_migration_names(["0004_AddPeople.py"])[0]


def test_command_names() -> None:
    assert check_command_names(["term_close", "security_create_administrator", "migrate", "createsuperuser"]) == []
    assert check_command_names(["termclose", "Term_close"]) == [
        "command [termclose] should be named context_action (original context:action)",
        "command [Term_close] should be named context_action (original context:action)",
    ]


def test_translation_msgids_are_english_source_text() -> None:
    assert check_catalog_entries([("portal", "Welcome, %(name)s"), (None, "Home")], "x.po") == []
    assert check_catalog_entries([(None, "registration.errors.credit_limit_exceeded")], "x.po") == [
        "x.po: msgid [registration.errors.credit_limit_exceeded] looks like a translation key; "
        "use the English source text"
    ]
    assert "msgctxt [Admin Panel]" in check_catalog_entries([("Admin Panel", "Home")], "x.po")[0]


@pytest.mark.django_db
def test_passes_for_the_application() -> None:
    out = StringIO()

    assert call_command("naming_check", stdout=out, stderr=StringIO()) == 0, out.getvalue()
    assert "Names follow the conventions." in out.getvalue()
