"""Every synchronization step and its outcome (original Filament ``LmsSyncLogResource``). Read
only; the detail page shows the message and the payload."""

from __future__ import annotations

import json
from typing import Any, ClassVar

from django.contrib import admin
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.decorators import display

from ninefruits.adminpanel.mixins import ReadOnlyCatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.lms.enums import SyncOperation, SyncStatus
from ninefruits.lms.models import LmsSyncLog
from ninefruits.security.enums import Permission

from .course_links import PlatformFilter, shorten


class OperationFilter(admin.SimpleListFilter):
    title = _("Operation")
    parameter_name = "operation"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return list(SyncOperation.choices)

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        value = self.value()
        return queryset.filter(operation=value) if value else queryset


class SyncStatusFilter(admin.SimpleListFilter):
    title = pgettext_lazy("registration", "Status")
    parameter_name = "status"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return list(SyncStatus.choices)

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        value = self.value()
        return queryset.filter(status=value) if value else queryset


def _label(choices: Any, value: str) -> str:
    try:
        return str(choices(value).label)
    except ValueError:
        return value


@admin.register(LmsSyncLog)
class LmsSyncLogAdmin(ReadOnlyCatalogAdmin):
    permissions: ClassVar[dict[str, str]] = {"view": Permission.LMS_MANAGE}
    navigation_group = NavigationGroup.LMS
    navigation_icon = "list_alt"
    navigation_order = 30
    list_display = (
        "started_at",
        "platform_code",
        "operation_column",
        "section_label",
        "user_email",
        "status_column",
        "message_column",
    )
    list_filter = (PlatformFilter, OperationFilter, SyncStatusFilter)
    list_select_related = ("platform", "section__course", "user")
    ordering = ("-started_at", "-id")
    fields = (
        "started_at",
        "finished_at",
        "platform_code",
        "operation_column",
        "section_label",
        "user_email",
        "enrollment_id",
        "status_column",
        "message",
        "payload_column",
    )
    readonly_fields = fields

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self.policy_allows(request, "view_any", LmsSyncLog)

    @display(description=_("LMS platform"), ordering="platform__code")
    def platform_code(self, obj: LmsSyncLog) -> str:
        return obj.platform.code

    @display(description=_("Operation"))
    def operation_column(self, obj: LmsSyncLog) -> str:
        return _label(SyncOperation, obj.operation)

    @display(description=pgettext_lazy("offering", "Section"))
    def section_label(self, obj: LmsSyncLog) -> str:
        return obj.section.label() if obj.section is not None else "-"

    @display(description=_("User"))
    def user_email(self, obj: LmsSyncLog) -> str:
        return obj.user.email if obj.user is not None else "-"

    @display(
        description=pgettext_lazy("registration", "Status"),
        label={
            SyncStatus.SUCCEEDED.value: "success",
            SyncStatus.FAILED.value: "danger",
            SyncStatus.SKIPPED.value: "info",
            SyncStatus.QUEUED.value: "warning",
        },
    )
    def status_column(self, obj: LmsSyncLog) -> tuple[str, str]:
        return obj.status, _label(SyncStatus, obj.status)

    @display(description=_("Message"))
    def message_column(self, obj: LmsSyncLog) -> str:
        return shorten(obj.message, 60)

    @display(description=_("Payload"))
    def payload_column(self, obj: LmsSyncLog) -> str:
        if obj.payload is None:
            return "-"
        return format_html(
            '<pre class="whitespace-pre-wrap text-xs">{}</pre>',
            json.dumps(obj.payload, ensure_ascii=False, indent=2, sort_keys=True),
        )
