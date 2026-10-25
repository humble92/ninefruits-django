"""Read-only audit screens (original Filament Activities, RecordChanges and SecurityEvents
resources; AuditRecordPolicy and SecurityEventPolicy)."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.urls import reverse

from ninefruits.audit.logger import audit
from ninefruits.audit.models import ActivityLog, RecordChange, SecurityEvent
from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.security.enums import Permission
from tests.audit.support import make_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def auditor(client: Client, grant: Any) -> Any:
    user = grant(make_user(name="Auditor"), Permission.AUDIT_RECORDS_VIEW)
    client.force_login(user)
    return user


def test_lists_and_shows_activities_with_their_details(client: Client, auditor: Any) -> None:
    subject = make_user()
    activity = audit("users.updated", subject, reason="Typo fixed", properties={"field": "name"}, causer=auditor)

    listing = client.get(reverse("admin:audit_activitylog_changelist"))
    assert listing.status_code == 200
    content = listing.content.decode()
    assert "users.updated" in content and "Auditor" in content and f"User #{subject.pk}" in content

    filtered = client.get(reverse("admin:audit_activitylog_changelist"), {"log_name": "command"})
    assert "users.updated" not in filtered.content.decode()
    searched = client.get(reverse("admin:audit_activitylog_changelist"), {"q": "users.upd"})
    assert "users.updated" in searched.content.decode()

    detail = client.get(reverse("admin:audit_activitylog_change", args=[activity.pk]))
    assert detail.status_code == 200
    body = detail.content.decode()
    assert "Typo fixed" in body and "<th scope='row'>field</th><td>name</td>" in body


def test_shows_record_changes_with_a_before_and_after_comparison(client: Client, auditor: Any) -> None:
    user = make_user(name="Before")
    user.name = "After"
    user.save()
    change = RecordChange.objects.filter(table_name="users", record_id=str(user.pk), operation="UPDATE").latest("id")

    listing = client.get(reverse("admin:audit_recordchange_changelist"), {"table_name": "users", "operation": "UPDATE"})
    assert listing.status_code == 200
    assert "app_runtime" in listing.content.decode()

    detail = client.get(reverse("admin:audit_recordchange_change", args=[change.pk])).content.decode()
    assert "<tr class='changed'><th scope='row'>name</th><td>Before</td><td>After</td></tr>" in detail


def test_requires_the_audit_permission(client: Client, grant: Any) -> None:
    other = grant(make_user(), Permission.SECURITY_EVENTS_VIEW)
    client.force_login(other)

    assert client.get(reverse("admin:audit_activitylog_changelist")).status_code == 403
    assert client.get(reverse("admin:audit_recordchange_changelist")).status_code == 403
    assert client.get(reverse("admin:audit_securityevent_changelist")).status_code == 200


def test_lists_security_events_for_holders_of_their_permission_only(client: Client, auditor: Any, grant: Any) -> None:
    record_security_event(SecurityEventType.LOGIN_FAILED, identifier="intruder@example.test")

    assert client.get(reverse("admin:audit_securityevent_changelist")).status_code == 403

    grant(auditor, Permission.SECURITY_EVENTS_VIEW)
    listing = client.get(reverse("admin:audit_securityevent_changelist"), {"type": "login.failed"})
    assert listing.status_code == 200
    assert "intruder@example.test" in listing.content.decode()
    assert "Sign-in failed" in listing.content.decode()


def test_audit_records_cannot_be_added_changed_or_deleted(client: Client, auditor: Any) -> None:
    activity = audit("test.readonly")

    assert client.get(reverse("admin:audit_activitylog_add")).status_code == 403
    assert client.post(reverse("admin:audit_activitylog_delete", args=[activity.pk])).status_code == 403
    assert ActivityLog.objects.filter(pk=activity.pk).exists()


def test_querysets_are_empty_without_the_permission(grant: Any) -> None:
    viewer = make_user()
    audit("test.hidden")

    assert ActivityLog.objects.visible_to(viewer).count() == 0
    assert SecurityEvent.objects.visible_to(viewer).count() == 0
    grant(viewer, Permission.AUDIT_RECORDS_VIEW)
    assert ActivityLog.objects.visible_to(viewer).count() >= 1
    assert SecurityEvent.objects.visible_to(viewer).count() == 0
