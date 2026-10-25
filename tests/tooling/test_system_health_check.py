"""``system_health_check`` (original ``OperationsCommandsTest`` "reports the system health")."""

from __future__ import annotations

import json
from io import StringIO
from typing import Any

import httpx
import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from ninefruits.core.tasks import HEARTBEAT_CACHE_KEY
from tests.reference_conftest import essential_data  # noqa: F401

pytestmark = [pytest.mark.django_db(databases=["default", "migrator"]), pytest.mark.usefixtures("essential_data")]


@pytest.fixture(autouse=True)
def _gotenberg_and_heartbeat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(httpx, "get", lambda url, **kwargs: httpx.Response(200, request=httpx.Request("GET", url)))
    cache.set(HEARTBEAT_CACHE_KEY, timezone.now().isoformat(), 600)


def _run(*args: str) -> tuple[int, str]:
    out = StringIO()
    code = call_command("system_health_check", *args, stdout=out, stderr=StringIO())
    return int(code), out.getvalue()


def test_reports_the_system_health() -> None:
    code, output = _run("--json")
    report: dict[str, Any] = json.loads(output)

    failed = {check["check"]: check["detail"] for check in report["checks"] if not check["ok"]}
    assert failed == {}
    assert report["ok"] is True and len(report["checks"]) == 12 and code == 0


def test_a_missing_key_fails_the_check_with_exit_code_2() -> None:
    with override_settings(PII_HASH_KEY=""):
        code, output = _run()

    assert code == 2
    assert "pii_keys" in output and "FAIL" in output


def test_unsynced_permissions_are_named() -> None:
    from ninefruits.security.models import Permission as PermissionRecord

    PermissionRecord.objects.filter(name="people.view").delete()
    code, output = _run("--json")

    checks = {check["check"]: check for check in json.loads(output)["checks"]}
    assert code == 2 and not checks["permissions"]["ok"] and "people.view" in checks["permissions"]["detail"]
