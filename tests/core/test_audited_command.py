"""Original tests/Feature/Tooling/AuditedCommandTest.php: the AuditedCommand base records each run
(options, operating system user, actor, exit code, result) in the business audit, rejects an
unknown ``--actor``, supports dry runs and exit code 2, and audits failures."""

from __future__ import annotations

from io import StringIO
from typing import Any

import pytest
from django.core.management import call_command
from django.core.management.base import CommandParser

from ninefruits.audit.models import ActivityLog
from ninefruits.core import commands, context
from ninefruits.core.commands import AuditedCommand, StatusCommand
from ninefruits.core.db import session_context
from tests.audit.support import make_user

pytestmark = pytest.mark.django_db


class SampleCommand(AuditedCommand):
    """Stands in for a data changing command (the original test used security:sync-permissions)."""

    command_name = "sample_change"
    seen: dict[str, Any] = {}

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("target", nargs="?")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--reason")
        parser.add_argument("--password")
        parser.add_argument("--fail", action="store_true")
        parser.add_argument("--exit", type=int, default=0)

    def handle(self, *args: Any, **options: Any) -> int:
        SampleCommand.seen = {
            "db": session_context().current(),
            "request_id": context.current().request_id,
            "dry_run": self.is_dry_run(),
        }
        if options["fail"]:
            raise RuntimeError("Something broke")
        if self.is_dry_run():
            self.stdout.write("legacy.removed")
        self.record_result({"changed": 0 if self.is_dry_run() else 3})
        return int(options["exit"])


def run(*args: str, **options: Any) -> tuple[int, str]:
    out, err = StringIO(), StringIO()
    code = call_command(SampleCommand(), *args, stdout=out, stderr=err, **options)
    return code, out.getvalue() + err.getvalue()


def command_runs() -> Any:
    return ActivityLog.objects.filter(event="command.executed")


def test_records_the_run_options_operating_system_user_and_exit_code_in_the_business_audit() -> None:
    admin = make_user("ops@example.test")

    code, _ = run("records", actor="ops@example.test", reason="Yearly clean-up", password="hunter2")

    assert code == 0
    activity = command_runs().get()
    assert activity.log_name == "command"
    assert activity.description == "command.executed"
    assert activity.causer_id == admin.pk
    assert activity.reason == "Yearly clean-up"
    assert activity.properties["command"] == "sample_change"
    assert activity.properties["exit_code"] == 0
    assert activity.properties["os_user"]
    assert activity.properties["arguments"] == {"target": "records"}
    assert activity.properties["options"]["actor"] == "ops@example.test"
    assert activity.properties["options"]["password"] == "[redacted]"
    assert "verbosity" not in activity.properties["options"] and "force" not in activity.properties["options"]
    assert activity.properties["dry_run"] is False
    assert activity.properties["result"] == {"changed": 3}


def test_gives_the_run_an_id_and_the_system_database_context() -> None:
    run()

    activity = command_runs().get()
    assert activity.request_id.startswith("cmd-")
    assert SampleCommand.seen["request_id"] == activity.request_id
    assert SampleCommand.seen["db"]["app.actor"] == "system:command:sample_change"
    assert SampleCommand.seen["db"]["app.request_id"] == activity.request_id
    assert SampleCommand.seen["db"]["app.user_id"] == ""
    # The context of the caller comes back afterwards.
    assert session_context().current()["app.actor"] == "system:test"
    assert context.current().request_id is None


def test_keeps_an_existing_request_id() -> None:
    with context.bound(request_id="req-from-caller"):
        run()

    assert command_runs().get().request_id == "req-from-caller"


def test_rejects_an_unknown_actor() -> None:
    code, output = run(actor="nobody@example.test")

    assert code == 1
    assert "No user with the email [nobody@example.test] for --actor." in output
    assert not command_runs().exists()


def test_changes_nothing_in_a_dry_run() -> None:
    code, output = run(dry_run=True)

    assert code == 0 and "legacy.removed" in output
    activity = command_runs().get()
    assert activity.properties["dry_run"] is True
    assert activity.properties["options"] == {"dry_run": True, "exit": 0}
    assert activity.properties["result"] == {"changed": 0}


def test_returns_and_records_the_exit_code() -> None:
    code, _ = run(exit=commands.PROBLEMS_FOUND)

    assert code == 2 == AuditedCommand.PROBLEMS_FOUND
    assert command_runs().get().properties["exit_code"] == 2


def test_records_a_failure_and_raises_the_original_exception() -> None:
    with pytest.raises(RuntimeError, match="Something broke"):
        run(fail=True)

    activity = command_runs().get()
    assert activity.properties["exit_code"] == 1
    assert activity.properties["result"] == {"exception": "RuntimeError", "message": "Something broke"}
    assert session_context().current()["app.actor"] == "system:test"


def test_skips_the_audit_with_a_warning_before_the_audit_tables_exist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(commands, "_audit_tables_exist", lambda: False)

    code, output = run()

    assert code == 0
    assert "The audit tables do not exist yet; this run was not recorded." in output
    assert not command_runs().exists()


class CheckCommand(StatusCommand):
    def handle(self, *args: Any, **options: Any) -> int:
        return self.PROBLEMS_FOUND


def test_check_commands_return_exit_code_2_without_an_audit() -> None:
    assert call_command(CheckCommand(), stdout=StringIO()) == 2
    assert not command_runs().exists()


def test_manage_py_exits_with_the_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    command = CheckCommand()
    monkeypatch.setattr("django.db.connections.close_all", lambda: None)
    with pytest.raises(SystemExit) as exit_info:
        command.run_from_argv(["manage.py", "check_sample", "--skip-checks"])
    assert exit_info.value.code == 2
