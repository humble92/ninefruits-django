"""Unmanaged models over the ``audit`` schema with the quoting trick
``db_table = 'audit"."activity_log'`` (porting-plan 5.3: "Phase 0에서 이 기법의 동작을 테스트로
고정"). Querying, ordering, filtering, INSERT with RETURNING, the append-only rules and the
migration autodetector are pinned here."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.apps import apps
from django.db import connection
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.utils import timezone

from ninefruits.audit.models import ActivityLog, AppendOnlyError, RecordChange, SecurityEvent
from ninefruits.audit.security_events import SecurityEventType
from tests.audit.support import database_error, make_user
from tests.factories.audit import ActivityLogFactory, SecurityEventFactory

pytestmark = pytest.mark.django_db


def test_quoted_table_names_resolve_to_the_audit_schema() -> None:
    sql = str(ActivityLog.objects.filter(event="x").query)
    assert '"audit"."activity_log"' in sql
    assert '"audit"."activity_log"."event"' in sql
    for model, table in (
        (ActivityLog, "activity_log"),
        (RecordChange, "record_changes"),
        (SecurityEvent, "security_events"),
    ):
        assert model._meta.managed is False
        assert model._meta.db_table == f'audit"."{table}'
        assert connection.ops.quote_name(model._meta.db_table) == f'"audit"."{table}"'


def test_insert_returns_the_id_and_the_trigger_sets_the_row_hash() -> None:
    activity = ActivityLogFactory(event="test.inserted", properties={"a": 1})

    assert activity.pk is not None
    activity.refresh_from_db()
    assert activity.description == "test.inserted"
    assert activity.properties == {"a": 1}
    assert activity.row_hash is not None and len(activity.row_hash) == 64
    assert activity.chain_hash is None and activity.sealed_at is None


def test_filtering_ordering_and_aggregation_work_through_the_orm() -> None:
    now = timezone.now()
    older = ActivityLogFactory(event="test.order", log_name="a", created_at=now - timedelta(days=2))
    newer = ActivityLogFactory(event="test.order", log_name="b", created_at=now)

    queryset = ActivityLog.objects.filter(event="test.order")
    assert list(queryset.order_by("-created_at").values_list("pk", flat=True)) == [newer.pk, older.pk]
    assert list(queryset.order_by("log_name").values_list("log_name", flat=True)) == ["a", "b"]
    assert queryset.filter(created_at__lt=now - timedelta(days=1)).get() == older
    assert queryset.filter(properties__has_key="nothing").count() == 0
    assert set(queryset.values_list("log_name", flat=True).distinct()) == {"a", "b"}


def test_security_events_join_their_user() -> None:
    user = make_user()
    event = SecurityEventFactory(type=SecurityEventType.LOGOUT.value, user_id=user.pk)

    loaded = SecurityEvent.objects.select_related("user").get(pk=event.pk)
    assert loaded.user == user
    assert loaded.event_type is SecurityEventType.LOGOUT
    assert SecurityEvent.objects.filter(user__email=user.email).count() == 1


def test_record_changes_are_read_only_for_the_application() -> None:
    user = make_user()
    change = RecordChange.objects.filter(table_name="users", record_id=str(user.pk), operation="INSERT").get()

    assert change.database_user == "app_runtime"
    assert change.new_values["email"] == user.email
    with pytest.raises(AppendOnlyError):
        change.save()
    with pytest.raises(AppendOnlyError):
        RecordChange(table_schema="public", table_name="users", operation="INSERT", database_user="x").save()


def test_activity_records_are_append_only() -> None:
    activity = ActivityLogFactory()

    with pytest.raises(AppendOnlyError):
        activity.save()
    with pytest.raises(AppendOnlyError):
        activity.delete()
    # Bypassing the model still fails in the database.
    assert "permission denied" in database_error(lambda: ActivityLog.objects.filter(pk=activity.pk).update(reason="x"))
    assert "permission denied" in database_error(lambda: SecurityEvent.objects.all().delete())


def test_the_migration_autodetector_ignores_the_unmanaged_tables() -> None:
    loader = MigrationLoader(None, ignore_no_migrations=True)
    autodetector = MigrationAutodetector(loader.project_state(), ProjectState.from_apps(apps))
    changes = autodetector.changes(graph=loader.graph)

    assert "audit" not in changes
    state = loader.project_state().models
    assert state["audit", "activitylog"].options["managed"] is False
    # Unmanaged models never get indexes or constraints in the migration state, so Django never
    # tries to create or rename the original's indexes (activity_log_subject, ...).
    assert state["audit", "activitylog"].options.get("indexes", []) == []


def test_the_original_indexes_exist_on_the_audit_tables() -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT indexname FROM pg_indexes WHERE schemaname = 'audit' AND tablename = 'activity_log'")
        names = {row[0] for row in cursor.fetchall()}
    assert {"activity_log_subject", "activity_log_causer", "audit_activity_log_request_id_index"} <= names
