"""Raw SQL must be a constant string (original ``tools/phpstan/Rules/NoDynamicRawSqlRule.php``).

Values go in the parameters, never into the SQL text (porting-plan 11). The check parses the
sources (``ast``) and reports SQL passed to

- ``<cursor>.execute(sql, ...)`` / ``.executemany(sql, ...)`` (including
  ``connection.cursor().execute``),
- ``RawSQL(sql, ...)``, ``<manager>.raw(sql, ...)`` and ``migrations.RunSQL(sql, ...)``,

when ``sql`` is built with an f-string, ``%``, ``.format()``, ``+`` or ``str.join``, or is a
variable/attribute that is not (only) assigned such safe values. Safe values: string constants,
``ninefruits.core.db.SqlFile.read(...)``, psycopg ``sql.SQL(...)`` compositions, constant
look-ups in literal dicts/tuples (allow lists), and names assigned only safe values in the same
function, class or module. ``.extra()`` is always forbidden.

Intentional exceptions carry a marker with a reason on the call's line(s)::

    cursor.execute(statement)  # raw-sql: ok (identifiers from the ALLOWED_TABLES allow list)

Usage: ``uv run tools/checks/raw_sql.py [paths...]`` (default: ninefruits config tools).
Exit code 0 when clean, 1 when problems were found.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATHS = ("ninefruits", "config", "tools")
EXCLUDED_PARTS = {"__pycache__", ".venv", "node_modules"}
#: Example code of the checker's own tests.
EXCLUDED_FILES = {"raw_sql_examples.py"}

STATEMENT_METHODS = {"execute", "executemany"}
RAW_CALLABLES = {"RawSQL", "RunSQL"}
RAW_METHODS = {"raw"}
FORBIDDEN_METHODS = {"extra"}

MARKER = re.compile(r"#\s*raw-sql:\s*ok\b\s*(\((?P<reason>[^)]*)\))?")

MESSAGE = (
    "Raw SQL passed to {target}() is not a constant string ({why}). "
    "Use parameters for values, or an allow list for identifiers."
)


@dataclass(frozen=True)
class Problem:
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _call_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


class _Scope:
    """Assignments by name in one function, class or module body (nested scopes excluded)."""

    def __init__(self, node: ast.AST, parent: _Scope | None) -> None:
        self.node = node
        self.parent = parent
        self.assignments: dict[str, list[ast.expr | None]] = {}
        body = getattr(node, "body", [])
        for statement in body if isinstance(body, list) else []:
            self._collect(statement)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            arguments = node.args
            for arg in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]:
                self.assignments.setdefault(arg.arg, []).append(None)
            for extra in (arguments.vararg, arguments.kwarg):
                if extra is not None:
                    self.assignments.setdefault(extra.arg, []).append(None)

    def _collect(self, node: ast.AST) -> None:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Lambda):
            if not isinstance(node, ast.Lambda):
                self.assignments.setdefault(node.name, []).append(None)
            return
        if isinstance(node, ast.Assign):
            for target in node.targets:
                self._bind(target, node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            self.assignments.setdefault(node.target.id, []).append(node.value)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            # ``sql += ...`` builds a string from pieces: unsafe unless the piece is safe and
            # the name is otherwise safe; model it as a concatenation.
            self.assignments.setdefault(node.target.id, []).append(
                ast.BinOp(left=ast.Name(id=node.target.id), op=node.op, right=node.value)
            )
        elif isinstance(node, ast.For | ast.AsyncFor | ast.comprehension):
            self._bind_loop(node.target, node.iter)
        elif isinstance(node, ast.With | ast.AsyncWith):
            for item in node.items:
                if item.optional_vars is not None:
                    self._bind(item.optional_vars, None)
        elif isinstance(node, ast.NamedExpr):
            self._bind(node.target, node.value)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            for alias in node.names:
                self.assignments.setdefault((alias.asname or alias.name).split(".")[0], []).append(None)
        for child in ast.iter_child_nodes(node):
            self._collect(child)

    def _bind_loop(self, target: ast.AST, iterable: ast.expr) -> None:
        """``for v in ALLOWED`` / ``ALLOWED.values()`` / ``for k, v in ALLOWED.items()``: the
        loop value is an element of the container (checked like ``ALLOWED[...]``)."""
        container: ast.expr | None = None
        value_target: ast.AST | None = None
        if isinstance(iterable, ast.Call) and isinstance(iterable.func, ast.Attribute) and not iterable.args:
            if iterable.func.attr == "items" and isinstance(target, ast.Tuple) and len(target.elts) == 2:
                container, value_target = iterable.func.value, target.elts[1]
                self._bind(target.elts[0], None)
            elif iterable.func.attr == "values":
                container, value_target = iterable.func.value, target
        elif isinstance(iterable, ast.Name | ast.Tuple | ast.List):
            container, value_target = iterable, target
        if container is not None and isinstance(value_target, ast.Name):
            element = ast.Subscript(value=container, slice=ast.Constant(value=None), ctx=ast.Load())
            self.assignments.setdefault(value_target.id, []).append(element)
        else:
            self._bind(target, None)

    def _bind(self, target: ast.AST, value: ast.expr | None) -> None:
        if isinstance(target, ast.Name):
            self.assignments.setdefault(target.id, []).append(value)
        elif isinstance(target, ast.Tuple | ast.List):
            for element in target.elts:
                self._bind(element, None)
        elif isinstance(target, ast.Starred):
            self._bind(target.value, None)

    def lookup(self, name: str) -> tuple[list[ast.expr | None], _Scope] | None:
        scope: _Scope | None = self
        while scope is not None:
            if name in scope.assignments:
                return scope.assignments[name], scope
            scope = scope.parent
            # Class bodies are not visible from their methods.
            while scope is not None and isinstance(scope.node, ast.ClassDef) and scope is not self:
                scope = scope.parent
        return None


class _Checker(ast.NodeVisitor):
    def __init__(self, path: str, source: str) -> None:
        self.path = path
        self.lines = source.splitlines()
        self.problems: list[Problem] = []
        self.scope: _Scope | None = None
        self.classes: list[_Scope] = []

    # -- scopes ----------------------------------------------------------------------------
    def _enter(self, node: ast.AST) -> None:
        previous = self.scope
        self.scope = _Scope(node, previous)
        is_class = isinstance(node, ast.ClassDef)
        if is_class:
            self.classes.append(self.scope)
        self.generic_visit(node)
        if is_class:
            self.classes.pop()
        self.scope = previous

    def visit_Module(self, node: ast.Module) -> None:
        self._enter(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._enter(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._enter(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._enter(node)

    # -- calls -----------------------------------------------------------------------------
    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node.func)
        is_method = isinstance(node.func, ast.Attribute)
        if name in FORBIDDEN_METHODS and is_method:
            self._report(node, f"Do not use .{name}(): build the query with the ORM or a constant RawSQL.")
        elif (is_method and name in STATEMENT_METHODS | RAW_METHODS) or name in RAW_CALLABLES:
            sql = self._sql_argument(node)
            if sql is not None:
                why = self._unsafe(sql, set())
                if why is not None:
                    self._report(node, MESSAGE.format(target=name, why=why))
        self.generic_visit(node)

    @staticmethod
    def _sql_argument(node: ast.Call) -> ast.expr | None:
        if node.args and not isinstance(node.args[0], ast.Starred):
            return node.args[0]
        for keyword in node.keywords:
            if keyword.arg in {"sql", "query", "raw_query", "operation"}:
                return keyword.value
        return None

    def _report(self, node: ast.AST, message: str) -> None:
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start) or start
        for line in self.lines[start - 1 : end]:
            match = MARKER.search(line)
            if match:
                if (match.group("reason") or "").strip():
                    return
                self.problems.append(
                    Problem(self.path, start, "raw-sql marker needs a reason: # raw-sql: ok (<reason>)")
                )
                return
        self.problems.append(Problem(self.path, start, message))

    # -- expression safety -----------------------------------------------------------------
    def _unsafe(self, node: ast.expr | None, seen: set[int]) -> str | None:
        """None when ``node`` is a safe SQL string, else a short reason."""
        if node is None:
            return "variable"
        if id(node) in seen:
            return None
        seen = seen | {id(node)}
        if isinstance(node, ast.Constant):
            return None if isinstance(node.value, str | bytes) or node.value is None else "not a string"
        if isinstance(node, ast.JoinedStr):
            return "f-string" if any(isinstance(v, ast.FormattedValue) for v in node.values) else None
        if type(node).__name__ == "TemplateStr":
            return "template string"
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Mod):
                return "% formatting"
            if isinstance(node.op, ast.Add):
                if self._unsafe(node.left, seen) is None and self._unsafe(node.right, seen) is None:
                    return None
                return "+ concatenation"
            return "expression"
        if isinstance(node, ast.IfExp):
            return self._unsafe(node.body, seen) or self._unsafe(node.orelse, seen)
        if isinstance(node, ast.Call):
            return self._unsafe_call(node, seen)
        if isinstance(node, ast.Name):
            return self._unsafe_name(node.id, seen)
        if isinstance(node, ast.Attribute):
            return self._unsafe_attribute(node, seen)
        if isinstance(node, ast.Subscript):
            return self._unsafe_subscript(node, seen)
        return "expression"

    def _unsafe_call(self, node: ast.Call, seen: set[int]) -> str | None:
        func = node.func
        name = _call_name(func)
        if self._is_sqlfile_read(func) or self._is_psycopg_sql(node):
            return None
        if isinstance(func, ast.Attribute) and name == "format":
            return None if self._is_psycopg_sql(func.value) else ".format()"
        if isinstance(func, ast.Attribute) and name == "join":
            if self._is_psycopg_sql(func.value):
                return None
            if len(node.args) == 1 and self._unsafe(func.value, seen) is None and self._safe_pieces(node.args[0], seen):
                return None
            return "str.join"
        return "function result"

    def _safe_pieces(self, node: ast.expr, seen: set[int]) -> bool:
        """A literal list/tuple of safe strings, possibly repeated (``["%s"] * len(values)``)."""
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            return self._safe_pieces(node.left, seen) or self._safe_pieces(node.right, seen)
        if isinstance(node, ast.List | ast.Tuple):
            return all(self._unsafe(element, seen) is None for element in node.elts)
        return False

    def _is_sqlfile_read(self, func: ast.expr) -> bool:
        if not (isinstance(func, ast.Attribute) and func.attr == "read"):
            return False
        owner = func.value
        if _call_name(owner) == "SqlFile" and isinstance(owner, ast.Name | ast.Attribute):
            return True
        in_sqlfile = any(
            isinstance(scope.node, ast.ClassDef) and scope.node.name == "SqlFile" for scope in self.classes
        )
        return in_sqlfile and isinstance(owner, ast.Name) and owner.id in {"cls", "self"}

    @staticmethod
    def _is_psycopg_sql(node: ast.expr) -> bool:
        """``sql.SQL("...")`` (psycopg composition; identifiers and literals are escaped)."""
        while (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"format", "join"}
        ):
            node = node.func.value
        return (
            isinstance(node, ast.Call)
            and _call_name(node.func) in {"SQL", "Composed"}
            and all(isinstance(arg, ast.Constant) and isinstance(arg.value, str) for arg in node.args)
        )

    def _unsafe_name(self, name: str, seen: set[int]) -> str | None:
        found = self.scope.lookup(name) if self.scope else None
        if found is None:
            return "variable"
        values, _scope = found
        for value in values:
            if value is None:
                return "variable"
            why = self._unsafe(value, seen)
            if why is not None:
                return why if why != "expression" else "variable"
        return None

    def _unsafe_attribute(self, node: ast.Attribute, seen: set[int]) -> str | None:
        # self.QUERY / cls.QUERY / ClassName.QUERY: a constant class attribute.
        for scope in reversed(self.classes):
            values = scope.assignments.get(node.attr)
            if values:
                for value in values:
                    if value is None or self._unsafe(value, seen) is not None:
                        return "attribute"
                return None
        return "attribute"

    def _unsafe_subscript(self, node: ast.Subscript, seen: set[int]) -> str | None:
        """``ALLOWED[key]`` where ``ALLOWED`` is a literal dict/tuple/list of safe strings."""
        container = node.value
        literal: ast.expr | None = container
        if isinstance(container, ast.Name) and self.scope is not None:
            found = self.scope.lookup(container.id)
            literal = found[0][0] if found and len(found[0]) == 1 else None
        if isinstance(literal, ast.Dict):
            values: Iterable[ast.expr | None] = literal.values
        elif isinstance(literal, ast.Tuple | ast.List | ast.Set):
            values = literal.elts
        else:
            return "subscript"
        return None if all(self._unsafe(value, seen) is None for value in values) else "subscript"


def check_source(source: str, path: str = "<string>") -> list[Problem]:
    tree = ast.parse(source, filename=path)
    checker = _Checker(path, source)
    checker.visit(tree)
    return sorted(checker.problems, key=lambda problem: problem.line)


def iter_files(paths: Iterable[str | Path]) -> Iterator[Path]:
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = ROOT / path
        candidates = [path] if path.is_file() else sorted(path.rglob("*.py"))
        for candidate in candidates:
            if EXCLUDED_PARTS & set(candidate.parts) or candidate.name in EXCLUDED_FILES:
                continue
            yield candidate


def check_paths(paths: Iterable[str | Path]) -> list[Problem]:
    problems: list[Problem] = []
    for file in iter_files(paths):
        relative = file.relative_to(ROOT) if file.is_relative_to(ROOT) else file
        problems.extend(check_source(file.read_text(encoding="utf-8"), str(relative)))
    return problems


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    problems = check_paths(arguments or DEFAULT_PATHS)
    for problem in problems:
        print(problem)
    if problems:
        print(f"{len(problems)} raw SQL problem(s). See tools/checks/raw_sql.py.", file=sys.stderr)
        return 1
    print("Raw SQL: no dynamic SQL found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
