"""Base classes for management commands (porting-plan 13.2, original AuditedCommand).

``handle()`` returns the exit code (0 success, 1 failure or cancelled, 2 a check found
problems) or ``None`` for success. ``manage.py`` exits with it; ``call_command`` returns it.

:class:`AuditedCommand` is the base for commands that change data:

- records the run in the business audit (log ``command``, event ``command.executed``): command,
  arguments, options, operating system user, optional ``--actor`` account, exit code, dry run
  flag and the result set with :meth:`AuditedCommand.record_result`;
- adds ``--actor=<email>`` so an administrator can be named as the person responsible;
- gives the run an id (``cmd-<uuid>``) in the request id slot, shared by its audit entry, the
  row changes it makes (database session context ``system:command:<name>``) and the Celery
  tasks it dispatches;
- commands that support ``--dry-run`` declare the option and call :meth:`is_dry_run`.

Read-only check commands extend :class:`StatusCommand` (exit codes, no audit)."""

from __future__ import annotations

import contextlib
import getpass
import os
import sys
import uuid
from argparse import ArgumentParser
from typing import Any, ClassVar

from django.core.management.base import BaseCommand, CommandParser
from django.db import connection

from ninefruits.core import context
from ninefruits.core.db import session_context

SUCCESS = 0
FAILURE = 1
PROBLEMS_FOUND = 2

# Options every Django command has; not part of what an operator chose.
_FRAMEWORK_OPTIONS = frozenset(
    {"verbosity", "settings", "pythonpath", "traceback", "no_color", "force_color", "skip_checks", "stdout", "stderr"}
)


class StatusCommand(BaseCommand):
    """A command whose ``handle()`` returns an exit code."""

    SUCCESS: ClassVar[int] = SUCCESS
    FAILURE: ClassVar[int] = FAILURE
    PROBLEMS_FOUND: ClassVar[int] = PROBLEMS_FOUND

    exit_code: int = SUCCESS

    def handle(self, *args: Any, **options: Any) -> int | None:  # type: ignore[override]
        """Returns the exit code (``None`` = success)."""
        raise NotImplementedError

    def execute(self, *args: Any, **options: Any) -> Any:
        self.exit_code = SUCCESS
        handle = self.handle

        def run(*handle_args: Any, **handle_options: Any) -> None:
            status = handle(*handle_args, **handle_options)
            self.exit_code = SUCCESS if status is None else int(status)

        self.handle = run  # type: ignore[method-assign]
        try:
            super().execute(*args, **options)
        finally:
            del self.handle
        return self.exit_code

    def run_from_argv(self, argv: list[str]) -> None:
        super().run_from_argv(argv)
        if self.exit_code:
            sys.exit(self.exit_code)

    # -- output helpers (Laravel console components) --------------------------------------------
    def info(self, message: str) -> None:
        self.stdout.write(self.style.SUCCESS(message))

    def warn(self, message: str) -> None:
        self.stderr.write(self.style.WARNING(message))

    def error(self, message: str) -> None:
        self.stderr.write(self.style.ERROR(message))

    def detail(self, label: str, value: str) -> None:
        self.stdout.write(f"  {label} {'.' * max(2, 60 - len(label))} {value}")


class AuditedCommand(StatusCommand):
    """Base class for commands that change data. See the module docstring."""

    #: Command name for the audit and the database actor. Defaults to the module name
    #: (``ninefruits/pii/management/commands/pii_reencrypt.py`` -> ``pii_reencrypt``).
    command_name: ClassVar[str | None] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._result: dict[str, Any] = {}
        self._options: dict[str, Any] = {}
        self._positional: set[str] = set()

    @property
    def name(self) -> str:
        return self.command_name or type(self).__module__.rsplit(".", 1)[-1]

    def create_parser(self, prog_name: str, subcommand: str, **kwargs: Any) -> CommandParser:
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.add_argument(
            "--actor",
            metavar="EMAIL",
            help="Email of the administrator responsible for this run (recorded in the audit)",
        )
        self._positional = _positional_dests(parser)
        return parser

    # -- API for subclasses ---------------------------------------------------------------------
    def record_result(self, result: dict[str, Any]) -> None:
        self._result.update(result)

    def is_dry_run(self) -> bool:
        return bool(self._options.get("dry_run"))

    def actor(self) -> Any:
        from django.contrib.auth import get_user_model

        email = self._options.get("actor")
        if not isinstance(email, str) or email == "":
            return None
        return get_user_model()._default_manager.filter(email=email).first()

    # -- run ------------------------------------------------------------------------------------
    def execute(self, *args: Any, **options: Any) -> Any:
        self._result = {}
        self._options = dict(options)
        if not self._positional:
            self._positional = _positional_dests(self.create_parser("manage.py", self.name))
        request_id = context.current().request_id or f"cmd-{uuid.uuid4()}"
        db = session_context()
        # A command runs as the system: ``--actor`` is a claim by the operator, not a signed-in
        # user, so no user id reaches the row changes or the tasks it dispatches.
        with context.bound(request_id=request_id, user_id=None, actor=f"system:command:{self.name}"):
            db.enter_system(f"command:{self.name}", None, request_id)
            try:
                return self._run(args, options)
            finally:
                db.leave()

    def _run(self, args: tuple[Any, ...], options: dict[str, Any]) -> int:
        actor_email = options.get("actor")
        if isinstance(actor_email, str) and actor_email != "" and self.actor() is None:
            # Output streams are set up by BaseCommand.execute, which has not run yet.
            stderr = options.get("stderr") or sys.stderr
            stderr.write(self.style.ERROR(f"No user with the email [{actor_email}] for --actor.") + "\n")
            self.exit_code = FAILURE
            return FAILURE
        try:
            status = super().execute(*args, **options)
        except Exception as exception:
            # The audit write itself may fail (e.g. an aborted transaction): the original
            # error must surface.
            with contextlib.suppress(Exception):  # reported through the exception raised below
                self._audit(FAILURE, {"exception": type(exception).__name__, "message": str(exception)})
            raise
        self._audit(int(status))
        return int(status)

    def _audit(self, status: int, extra: dict[str, Any] | None = None) -> None:
        # Before the first migration there is nowhere to write.
        if not _audit_tables_exist():
            self.warn("The audit tables do not exist yet; this run was not recorded.")
            return

        from ninefruits.audit.logger import audit

        arguments = {
            name: value
            for name, value in self._options.items()
            if name in self._positional and value is not None and name not in _FRAMEWORK_OPTIONS
        }
        options = {
            name: value
            for name, value in self._options.items()
            if name not in self._positional
            and name not in _FRAMEWORK_OPTIONS
            and value is not None
            and value is not False
            and value != []
        }
        reason = self._options.get("reason")
        audit(
            "command.executed",
            None,
            reason=reason if isinstance(reason, str) else None,
            properties={
                "command": self.name,
                "arguments": _jsonable(arguments),
                "options": _jsonable(options),
                "os_user": operating_system_user(),
                "exit_code": status,
                "dry_run": self.is_dry_run(),
                "result": _jsonable({**self._result, **(extra or {})}),
            },
            causer=self.actor(),
            log="command",
        )


def operating_system_user() -> str:
    try:
        return getpass.getuser()
    except KeyError, OSError:
        return os.environ.get("USER", "") or str(os.getuid())


def _positional_dests(parser: ArgumentParser) -> set[str]:
    return {action.dest for action in parser._actions if not action.option_strings}


def _audit_tables_exist() -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT to_regclass('audit.activity_log') IS NOT NULL")
        return bool(cursor.fetchone()[0])


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, bool | int | float | str):
        return value
    return str(value)
