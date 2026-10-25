"""Raw SQL check (original tests/PHPStan/NoDynamicRawSqlRuleTest.php + data/raw-sql.php)."""

from __future__ import annotations

from pathlib import Path

from tools.checks import raw_sql

DATA = Path(__file__).parent / "data" / "raw_sql_examples.py"


def message(target: str, why: str) -> str:
    return raw_sql.MESSAGE.format(target=target, why=why)


def test_it_reports_raw_sql_built_from_variables() -> None:
    problems = raw_sql.check_source(DATA.read_text(encoding="utf-8"), "examples.py")

    assert [(problem.line, problem.message) for problem in problems] == [
        (25, message("execute", "f-string")),
        (26, message("execute", "% formatting")),
        (27, message("execute", ".format()")),
        (28, message("execute", "+ concatenation")),
        (29, message("execute", "variable")),
        (30, message("execute", "variable")),
        (31, message("RawSQL", "f-string")),
        (32, message("raw", "+ concatenation")),
        (33, "Do not use .extra(): build the query with the ORM or a constant RawSQL."),
        (35, message("executemany", "+ concatenation")),
        (37, "raw-sql marker needs a reason: # raw-sql: ok (<reason>)"),
    ]


def test_constant_sql_with_parameters_passes() -> None:
    source = 'def f(cursor, value):\n    cursor.execute("SELECT %s", [value])\n'

    assert raw_sql.check_source(source) == []


def test_module_and_class_constants_pass() -> None:
    source = (
        'QUERY = "SELECT 1"\n'
        "class Report:\n"
        '    SQL = "SELECT 2"\n'
        "    def run(self, cursor):\n"
        "        cursor.execute(QUERY)\n"
        "        cursor.execute(self.SQL)\n"
    )

    assert raw_sql.check_source(source) == []


def test_reassigned_names_are_checked_on_every_assignment() -> None:
    source = (
        "def f(cursor, column):\n"
        '    sql = "SELECT 1"\n'
        "    if column:\n"
        '        sql = f"SELECT {column}"\n'
        "    cursor.execute(sql)\n"
    )

    assert [problem.line for problem in raw_sql.check_source(source)] == [5]


def test_augmented_assignment_with_constants_passes_and_with_values_fails() -> None:
    ok = 'def f(cursor):\n    sql = "SELECT 1"\n    sql += " WHERE true"\n    cursor.execute(sql)\n'
    bad = 'def f(cursor, v):\n    sql = "SELECT 1"\n    sql += v\n    cursor.execute(sql)\n'

    assert raw_sql.check_source(ok) == []
    assert len(raw_sql.check_source(bad)) == 1


def test_the_application_has_no_dynamic_raw_sql() -> None:
    assert [str(problem) for problem in raw_sql.check_paths(raw_sql.DEFAULT_PATHS)] == []


def test_main_returns_one_on_problems(tmp_path: Path) -> None:
    file = tmp_path / "bad.py"
    file.write_text("def f(c, v):\n    c.execute(v)\n", encoding="utf-8")

    assert raw_sql.main([str(file)]) == 1
    assert raw_sql.main([str(tmp_path / "missing_dir")]) == 0
