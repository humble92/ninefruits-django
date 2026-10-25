"""The beat schedule (``config/celery.py``) names only registered tasks, and the scheduled
maintenance runs are audited like the commands the original scheduler ran."""

from __future__ import annotations

from typing import Any

import pytest

from config.celery import app
from ninefruits.audit.models import ActivityLog


def test_every_scheduled_task_is_registered() -> None:
    app.loader.import_default_modules()
    missing = sorted(entry["task"] for entry in app.conf.beat_schedule.values() if entry["task"] not in app.tasks)
    assert missing == []


@pytest.mark.django_db(databases=["default", "migrator"])
@pytest.mark.parametrize(
    ("task_name", "command"),
    [
        ("audit.seal", "audit_seal"),
        ("registration.promote_waitlists", "waitlist_promote"),
        ("admission.expire_drafts", "admission_expire_drafts"),
    ],
)
def test_scheduled_maintenance_is_audited_as_its_command(task_name: str, command: str, settings: Any) -> None:
    settings.CELERY_TASK_ALWAYS_EAGER = True
    app.loader.import_default_modules()
    app.tasks[task_name].apply().get()
    assert ActivityLog.objects.filter(log_name="command", properties__command=command).exists()
