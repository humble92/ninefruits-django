"""Original tests/Feature/Tooling/AuditCorrelationTest.php, the CSV import cases: row changes
made by queued imports and by ``reference_import`` must be traceable to who started them
(ADR 0002)."""

from __future__ import annotations

from collections.abc import Callable
from io import StringIO

import pytest
from django.core.management import call_command
from django.http import HttpRequest, JsonResponse
from django.test import Client
from django.urls import path

from ninefruits.audit.models import ActivityLog, RecordChange
from ninefruits.core.db import session_context
from ninefruits.importing.services import start_import
from ninefruits.organization.models import OrgUnit
from tests.factories.security import UserFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("essential_data")]

ROW = {"code": "AUD1", "type": "university", "name_en": "Audit University", "effective_start_date": "2000-01-01"}


def org_unit_change(code: str) -> RecordChange:
    unit = OrgUnit.objects.get(code=code)
    return RecordChange.objects.get(table_name="org_units", record_id=str(unit.pk), operation="INSERT")


def _import_view(request: HttpRequest) -> JsonResponse:
    # Same dispatch as the admin screen's import, inside an authenticated request.
    start_import("org_units", request.user, "org.csv", "imports/org.csv", [ROW])
    return JsonResponse({"user_id_after_job": session_context().current()["app.user_id"]})


urlpatterns = [path("_test/import", _import_view)]


@pytest.mark.urls(__name__)
@pytest.mark.usefixtures("without_baseline")
def test_records_the_signed_in_user_on_rows_changed_by_an_import_started_from_the_admin_panel(
    client: Client,
) -> None:
    staff = UserFactory()
    client.force_login(staff)

    response = client.post("/_test/import")

    change = org_unit_change("AUD1")
    assert change.user_id == staff.pk
    assert change.actor == "system:task:importing.import_chunk"
    assert change.request_id == response.headers["X-Request-Id"]
    # A task run synchronously gives the request its user context back.
    assert response.json()["user_id_after_job"] == str(staff.pk)


def test_ties_rows_changed_by_a_command_to_the_command_run(csv_file: Callable[[str, list[list[str]]], str]) -> None:
    UserFactory(email="ops@example.com")
    path_ = csv_file("org.csv", [list(ROW), list(ROW.values())])

    assert call_command("reference_import", "org_units", path_, actor="ops@example.com", stdout=StringIO()) == 0

    run = ActivityLog.objects.filter(log_name="command", event="command.executed").latest("id")
    change = org_unit_change("AUD1")
    assert run.request_id.startswith("cmd-")
    assert change.request_id == run.request_id
    # --actor is a claim by whoever runs the command, not a signed-in user.
    assert change.user_id is None
