"""Original tests/Feature/Tooling/AuditCorrelationTest.php: row changes made by Celery tasks and
commands must be traceable to who started them (ADR 0002). The request id (or the command run
id) is shared by the business audit, the row changes and the tasks dispatched.

The original exercised a Filament CSV import and ``reference:import`` (Phase 1); here a task
and a command write ``settings`` rows (an audited table) directly."""

from __future__ import annotations

from io import StringIO
from typing import Any

import pytest
from celery import shared_task
from django.core.management import call_command
from django.http import HttpRequest, JsonResponse
from django.test import Client
from django.urls import path

from ninefruits.audit.models import ActivityLog, RecordChange
from ninefruits.core.commands import AuditedCommand
from ninefruits.core.db import session_context
from ninefruits.core.tasks import SystemTask
from ninefruits.settings.models import SettingValue
from tests.audit.support import make_user

pytestmark = pytest.mark.django_db


@shared_task(name="tests.write_setting", base=SystemTask)
def write_setting(name: str) -> None:
    SettingValue.objects.create(group="correlation", name=name, payload={"value": 1})


def setting_change(name: str) -> RecordChange:
    setting = SettingValue.objects.get(group="correlation", name=name)
    return RecordChange.objects.get(table_name="settings", record_id=str(setting.pk), operation="INSERT")


def _dispatch_view(request: HttpRequest) -> JsonResponse:
    write_setting.delay("from_request")
    return JsonResponse({"user_id_after_task": session_context().current()["app.user_id"]})


urlpatterns = [path("_test/dispatch", _dispatch_view)]


@pytest.mark.urls(__name__)
@pytest.mark.usefixtures("without_baseline")
def test_records_the_signed_in_user_on_rows_changed_by_a_task_started_from_a_request(client: Client) -> None:
    staff = make_user()
    client.force_login(staff)

    response = client.post("/_test/dispatch")

    change = setting_change("from_request")
    assert change.user_id == staff.pk
    assert change.actor == "system:task:tests.write_setting"
    assert change.request_id == response.headers["X-Request-Id"]
    # A task run synchronously gives the request its user context back.
    assert response.json()["user_id_after_task"] == str(staff.pk)


class ImportSettingsCommand(AuditedCommand):
    command_name = "correlation_import"

    def handle(self, *args: Any, **options: Any) -> int:
        SettingValue.objects.create(group="correlation", name="from_command", payload={"value": 1})
        write_setting.delay("from_command_task")
        return self.SUCCESS


def test_ties_rows_changed_by_a_command_and_its_tasks_to_the_command_run() -> None:
    make_user("ops@example.test")

    call_command(ImportSettingsCommand(), actor="ops@example.test", stdout=StringIO())

    run = ActivityLog.objects.filter(log_name="command", event="command.executed").latest("id")
    change = setting_change("from_command")
    task_change = setting_change("from_command_task")
    assert run.request_id.startswith("cmd-")
    assert change.request_id == run.request_id
    assert change.actor == "system:command:correlation_import"
    assert task_change.request_id == run.request_id
    assert task_change.actor == "system:task:tests.write_setting"
    # --actor is a claim by whoever runs the command, not a signed-in user.
    assert change.user_id is None and task_change.user_id is None
