"""Read-only audit screens (original Filament resources Activities, RecordChanges and
SecurityEvents in the Audit navigation group)."""

from __future__ import annotations

import json
from typing import Any

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import OuterRef, QuerySet, Subquery
from django.http import HttpRequest
from django.utils.html import format_html, format_html_join
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.contrib.filters.admin import ChoicesDropdownFilter, DropdownFilter, RangeDateTimeFilter
from unfold.decorators import display

from ninefruits.adminpanel.mixins import ReadOnlyCatalogAdmin
from ninefruits.audit.models import ActivityLog, RecordChange, SecurityEvent
from ninefruits.security.enums import Permission


def _format_value(value: Any) -> str:
    """Scalars as they are, structures as JSON (original KeyValueEntry state)."""
    if value is None:
        return "-"
    if isinstance(value, str | int | float | bool):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def _key_value_table(values: dict[str, Any] | None) -> SafeString:
    if not values:
        return format_html("{}", "-")
    rows = format_html_join(
        "", "<tr><th scope='row'>{}</th><td>{}</td></tr>", ((key, _format_value(v)) for key, v in values.items())
    )
    return format_html("<table class='audit-key-values'><tbody>{}</tbody></table>", rows)


class _DistinctValuesFilter(DropdownFilter):
    """Options are the distinct values present in the table (original SelectFilter options)."""

    model: Any = None
    field: str = ""

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, str]]:
        values = (
            self.model._default_manager.exclude(**{f"{self.field}__isnull": True})
            .order_by(self.field)
            .values_list(self.field, flat=True)
            .distinct()
        )
        return [(value, value) for value in values]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Any]) -> QuerySet[Any]:
        value = self.value()
        return queryset.filter(**{self.field: value}) if value else queryset


class LogNameFilter(_DistinctValuesFilter):
    title = _("Log")
    parameter_name = "log_name"
    model = ActivityLog
    field = "log_name"


class TableNameFilter(_DistinctValuesFilter):
    title = _("Table")
    parameter_name = "table_name"
    model = RecordChange
    field = "table_name"


@admin.register(ActivityLog)
class ActivityLogAdmin(ReadOnlyCatalogAdmin):
    """Business audit (who did what and why)."""

    permissions = {"view": Permission.AUDIT_RECORDS_VIEW}
    navigation_icon = "assignment"
    navigation_order = 10
    list_display = ("occurred_at", "log", "event", "subject", "actor", "short_reason")
    list_filter = (LogNameFilter, ("created_at", RangeDateTimeFilter))
    list_filter_submit = True
    search_fields = ("event",)
    ordering = ("-created_at", "-id")
    show_full_result_count = False
    fields = ("occurred_at", "event", "actor", "subject", "reason", "properties_table", "request_id", "ip_address")
    readonly_fields = fields

    def get_queryset(self, request: HttpRequest) -> QuerySet[ActivityLog]:
        # The causer's name in the same query (original ->with('causer')).
        users = get_user_model()._default_manager.filter(pk=OuterRef("causer_id")).values("name")[:1]
        queryset: QuerySet[ActivityLog] = super().get_queryset(request)
        return queryset.annotate(causer_name=Subquery(users))

    @display(description=pgettext_lazy("admin", "Time"), ordering="created_at")
    def occurred_at(self, obj: ActivityLog) -> Any:
        return obj.created_at

    @display(description=_("Log"), label=True)
    def log(self, obj: ActivityLog) -> str | None:
        return obj.log_name

    @display(description=_("Record"))
    def subject(self, obj: ActivityLog) -> str:
        return obj.subject_display or "-"

    @display(description=_("User"))
    def actor(self, obj: ActivityLog) -> str:
        name = getattr(obj, "causer_name", None)
        if name and obj.causer_type == str(settings.AUTH_USER_MODEL).lower():
            return str(name)
        return f"#{obj.causer_id}" if obj.causer_id else "-"

    @display(description=_("Reason"))
    def short_reason(self, obj: ActivityLog) -> str:
        reason = obj.reason or ""
        return (reason[:40] + "...") if len(reason) > 40 else (reason or "-")

    @display(description=_("Details"))
    def properties_table(self, obj: ActivityLog) -> SafeString:
        return _key_value_table(obj.properties if isinstance(obj.properties, dict) else None)


@admin.register(RecordChange)
class RecordChangeAdmin(ReadOnlyCatalogAdmin):
    """Data audit written by database triggers, including changes made outside the application."""

    permissions = {"view": Permission.AUDIT_RECORDS_VIEW}
    navigation_icon = "database"
    navigation_order = 20
    list_display = ("occurred_at", "table_name", "operation_badge", "record_id", "changed", "actor", "database_user")
    list_filter = (TableNameFilter, ("operation", ChoicesDropdownFilter), ("occurred_at", RangeDateTimeFilter))
    list_filter_submit = True
    search_fields = ("table_name", "record_id")
    ordering = ("-occurred_at", "-id")
    show_full_result_count = False
    fields = (
        "occurred_at",
        "table_name",
        "operation",
        "record_id",
        "actor",
        "database_user",
        "transaction_id",
        "request_id",
        "values_diff",
    )
    readonly_fields = fields

    @display(description=pgettext_lazy("admin", "Operation"), label=True)
    def operation_badge(self, obj: RecordChange) -> str:
        return obj.operation

    @display(description=_("Changed columns"))
    def changed(self, obj: RecordChange) -> str:
        text = ", ".join(obj.changed_columns or [])
        return (text[:40] + "...") if len(text) > 40 else (text or "-")

    @display(description=_("Changes"))
    def values_diff(self, obj: RecordChange) -> SafeString:
        """Column, before and after side by side; changed cells marked."""
        changed = set(obj.changed_columns or [])
        rows = format_html_join(
            "",
            "<tr class='{}'><th scope='row'>{}</th><td>{}</td><td>{}</td></tr>",
            (
                ("changed" if column in changed else "", column, _format_value(before), _format_value(after))
                for column, before, after in obj.diff()
            ),
        )
        return format_html(
            "<table class='audit-diff'><thead><tr><th>{}</th><th>{}</th><th>{}</th></tr></thead>"
            "<tbody>{}</tbody></table>",
            _("Column"),
            _("Before"),
            _("After"),
            rows,
        )


@admin.register(SecurityEvent)
class SecurityEventAdmin(ReadOnlyCatalogAdmin):
    permissions = {"view": Permission.SECURITY_EVENTS_VIEW}
    navigation_icon = "fingerprint"
    navigation_order = 30
    list_display = ("occurred_at", "type_badge", "user_name", "identifier", "subject", "ip_address")
    list_filter = (("type", ChoicesDropdownFilter), ("occurred_at", RangeDateTimeFilter))
    list_filter_submit = True
    list_select_related = ("user",)
    search_fields = ("identifier",)
    ordering = ("-occurred_at", "-id")
    show_full_result_count = False
    fields = (
        "occurred_at",
        "type",
        "user_name",
        "identifier",
        "subject",
        "properties_table",
        "request_id",
        "ip_address",
        "user_agent",
    )
    readonly_fields = fields

    @display(description=_("Event"), label=True)
    def type_badge(self, obj: SecurityEvent) -> str:
        return str(obj)

    @display(description=_("User"))
    def user_name(self, obj: SecurityEvent) -> str:
        user = obj.user if obj.user_id else None
        return str(user) if user is not None else "-"

    @display(description=_("Record"))
    def subject(self, obj: SecurityEvent) -> str:
        return obj.subject_display or "-"

    @display(description=_("Details"))
    def properties_table(self, obj: SecurityEvent) -> SafeString:
        return _key_value_table(obj.properties if isinstance(obj.properties, dict) else None)
