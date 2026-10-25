"""Business audit (AuditLogger) and security log (RecordSecurityEvent)."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import path

from ninefruits.audit.logger import audit, mask_sensitive
from ninefruits.audit.models import ActivityLog, SecurityEvent
from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.core import context
from tests.audit.support import make_user

pytestmark = pytest.mark.django_db


def test_records_event_subject_reason_properties_and_request_context() -> None:
    staff = make_user()
    subject = make_user()

    with context.bound(request_id="request-1", ip_address="10.0.0.1", user_agent="pytest", user_id=staff.pk):
        activity = audit("users.updated", subject, reason="Typo", properties={"field": "name"})

    activity.refresh_from_db()
    assert activity.log_name == "default"
    assert activity.event == "users.updated"
    assert activity.description == "users.updated"
    assert (activity.subject_type, activity.subject_id) == ("security.user", subject.pk)
    assert (activity.causer_type, activity.causer_id) == ("security.user", staff.pk)
    assert activity.causer == staff and activity.subject == subject
    assert activity.reason == "Typo"
    assert activity.properties == {"field": "name"}
    assert (activity.request_id, activity.ip_address, activity.user_agent) == ("request-1", "10.0.0.1", "pytest")
    assert activity.created_at is not None


def test_an_explicit_causer_and_log_win_over_the_context() -> None:
    staff, actor = make_user(), make_user()

    with context.bound(user_id=staff.pk):
        activity = audit("command.executed", causer=actor, log="command")

    assert (activity.causer_id, activity.log_name, activity.subject_type) == (actor.pk, "command", None)


def test_records_no_causer_without_a_user() -> None:
    activity = audit("system.happened")

    assert activity.causer_type is None and activity.causer_id is None
    assert activity.properties == {}


def test_masks_sensitive_property_values() -> None:
    activity = audit(
        "test.masked",
        properties={"password": "hunter2", "options": {"api-token": "abc", "chunk": 5}, "new_password": None},
    )

    assert activity.properties == {
        "password": "[redacted]",
        "options": {"api-token": "[redacted]", "chunk": 5},
        "new_password": None,
    }
    assert mask_sensitive([{"client_secret": "x"}, {"footprint": "kept"}]) == [
        {"client_secret": "[redacted]"},
        {"footprint": "kept"},
    ]


def test_records_security_events_with_the_request_context() -> None:
    user = make_user()

    with context.bound(request_id="request-2", ip_address="10.0.0.2", user_agent="agent"):
        event = record_security_event(
            SecurityEventType.ROLE_ASSIGNED, user=user, identifier=user.email, subject=user, properties={"role": "x"}
        )

    event.refresh_from_db()
    assert event.type == "role.assigned"
    assert event.user_id == user.pk
    assert (event.subject_type, event.subject_id) == ("security.user", user.pk)
    assert event.properties == {"role": "x"}
    assert (event.request_id, event.ip_address, event.user_agent) == ("request-2", "10.0.0.2", "agent")
    assert event.row_hash is not None


def test_empty_security_event_properties_are_stored_as_null() -> None:
    event = record_security_event(SecurityEventType.LOGIN_FAILED, identifier="nobody@example.test")

    assert SecurityEvent.objects.get(pk=event.pk).properties is None
    assert event.user_id is None


def test_every_security_event_type_has_a_label() -> None:
    for event_type in SecurityEventType:
        assert str(event_type.label)
    assert str(SecurityEventType.SENSITIVE_DATA_REVEALED.label) == "Sensitive data revealed"


def _audit_view(request):  # type: ignore[no-untyped-def]
    from django.http import JsonResponse

    activity = audit("test.from_request")
    return JsonResponse({"id": activity.pk})


urlpatterns = [path("_test/audit", _audit_view)]


@pytest.mark.urls(__name__)
def test_requests_attach_their_id_ip_address_and_user_agent(client: Client) -> None:
    user = make_user()
    client.force_login(user)

    response = client.get("/_test/audit", headers={"X-Request-Id": "req-12345678", "User-Agent": "Browser/1.0"})

    activity = ActivityLog.objects.get(pk=response.json()["id"])
    assert activity.request_id == "req-12345678" == response.headers["X-Request-Id"]
    assert activity.user_agent == "Browser/1.0"
    assert activity.ip_address == "127.0.0.1"
    assert activity.causer_id == user.pk
