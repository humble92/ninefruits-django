"""Factories for the audit tables (rows the application itself may write)."""

from __future__ import annotations

import factory

from ninefruits.audit.models import ActivityLog, SecurityEvent
from ninefruits.audit.security_events import SecurityEventType


class ActivityLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ActivityLog

    log_name = "default"
    event = factory.Sequence(lambda n: f"test.event_{n}")
    description = factory.SelfAttribute("event")
    properties = factory.LazyFunction(dict)


class SecurityEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SecurityEvent

    type = SecurityEventType.LOGIN_SUCCEEDED.value
    identifier = factory.Sequence(lambda n: f"user{n}@example.test")
