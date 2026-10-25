"""Idle session expiry (original session lifetime counts from the last request; security
review F3): the stored expiry moves forward with activity, at most every
``SESSION_REFRESH_SECONDS``, so active users are not signed out mid-work and idle ones are."""

from __future__ import annotations

import time
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.sessions.models import Session
from django.test import Client
from django.utils import timezone

from ninefruits.security.middleware import SESSION_REFRESHED_KEY
from tests.factories.security import UserFactory

pytestmark = pytest.mark.django_db


def _signed_in() -> Client:
    client = Client()
    client.force_login(UserFactory())
    return client


def _set(client: Client, *, refreshed_at: int, expires_in: timedelta) -> Session:
    session = client.session
    session[SESSION_REFRESHED_KEY] = refreshed_at
    session.save()
    Session.objects.filter(session_key=session.session_key).update(expire_date=timezone.now() + expires_in)
    return Session.objects.get(session_key=session.session_key)


def test_activity_pushes_the_expiry_forward() -> None:
    client = _signed_in()
    row = _set(
        client, refreshed_at=int(time.time()) - settings.SESSION_REFRESH_SECONDS - 1, expires_in=timedelta(minutes=10)
    )

    client.get("/portal/")

    row.refresh_from_db()
    remaining = row.expire_date - timezone.now()
    assert remaining > timedelta(seconds=settings.SESSION_COOKIE_AGE - 60)


def test_requests_within_the_interval_do_not_write_the_session() -> None:
    client = _signed_in()
    row = _set(client, refreshed_at=int(time.time()), expires_in=timedelta(minutes=10))
    before = row.expire_date

    client.get("/portal/")

    row.refresh_from_db()
    assert row.expire_date == before


def test_anonymous_sessions_are_not_extended() -> None:
    client = Client()
    client.get("/accounts/login/")
    assert all(SESSION_REFRESHED_KEY not in s.get_decoded() for s in Session.objects.all())
