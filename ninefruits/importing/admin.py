"""CSV import runs in the admin panel (original Filament import notifications and the failed
rows download)."""

from __future__ import annotations

from typing import Any, ClassVar

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from unfold.admin import TabularInline
from unfold.decorators import action, display

from ninefruits.adminpanel.mixins import CatalogPermissionMixin, ReadOnlyCatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.importing import registry
from ninefruits.importing.models import FailedImportRow, Import
from ninefruits.security.enums import Permission


def completion_message(import_run: Import, label: Any = None) -> str:
    """Original ``getCompletedNotificationTitle`` + ``getCompletedNotificationBody``."""
    if label is None:
        resource = registry.resource_for(import_run.importer)
        label = resource.label if resource else import_run.importer
    title = _("%(type)s import finished") % {"type": str(label)[:1].upper() + str(label)[1:]}
    body = _("%(count)s row(s) imported.") % {"count": f"{import_run.successful_rows:,}"}
    failed = import_run.failed_rows_count()
    if failed:
        body += " " + _("%(count)s row(s) failed; download the failed rows to fix them.") % {"count": f"{failed:,}"}
    return f"{title}. {body}"


class FailedImportRowInline(CatalogPermissionMixin, TabularInline):
    model = FailedImportRow
    fk_name = "import_run"
    extra = 0
    can_delete = False
    max_num = 0
    fields = ("data_display", "validation_error")
    readonly_fields = fields
    verbose_name = gettext_lazy("failed row")
    verbose_name_plural = gettext_lazy("failed rows")
    permissions: ClassVar[dict[str, str]] = {"view": Permission.ADMIN_PANEL_ACCESS}

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    @admin.display(description=gettext_lazy("Row"))
    def data_display(self, obj: FailedImportRow) -> str:
        return ", ".join(f"{key}={value}" for key, value in (obj.data or {}).items())


@admin.register(Import)
class ImportAdmin(ReadOnlyCatalogAdmin):
    """Everyone sees the imports they started; holders of ``reference_data.import`` see all."""

    permissions: ClassVar[dict[str, str]] = {"view": Permission.ADMIN_PANEL_ACCESS}
    navigation_group = NavigationGroup.REFERENCE_DATA
    navigation_icon = "upload_file"
    navigation_order = 95
    list_display = (
        "id",
        "type_column",
        "file_name",
        "user",
        "total_rows",
        "successful_rows",
        "status_column",
        "created_at",
    )
    list_select_related = ("user",)
    fields = (
        "type_column",
        "file_name",
        "user",
        "total_rows",
        "processed_rows",
        "successful_rows",
        "failed_rows_column",
        "status_column",
        "created_at",
        "completed_at",
    )
    readonly_fields = fields
    inlines = (FailedImportRowInline,)
    actions_detail = ("download_failed_rows",)

    def has_module_permission(self, request: HttpRequest) -> bool:
        return bool(request.user.has_perm(Permission.REFERENCE_DATA_IMPORT))

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if not request.user.has_perm(Permission.ADMIN_PANEL_ACCESS):
            return False
        return obj is None or obj.user_id == request.user.pk or request.user.has_perm(Permission.REFERENCE_DATA_IMPORT)

    @display(description=gettext_lazy("Import type"))
    def type_column(self, obj: Import) -> str:
        resource = registry.resource_for(obj.importer)
        return str(resource.label) if resource else obj.importer

    @display(description=gettext_lazy("Failed rows"))
    def failed_rows_column(self, obj: Import) -> int:
        return obj.failed_rows_count()

    @display(description=gettext_lazy("Status"))
    def status_column(self, obj: Import) -> str:
        return completion_message(obj) if obj.completed_at else _("Queued")

    def has_download_failed_rows_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        if object_id is None:
            return False
        import_run = Import.objects.filter(pk=object_id).first()
        return import_run is not None and self.has_view_permission(request, import_run)

    @action(
        description=gettext_lazy("Download failed rows"),
        url_path="failed-rows",
        permissions=["download_failed_rows"],
        icon="download",
    )
    def download_failed_rows(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        from ninefruits.importing.services import failed_rows_csv

        import_run = get_object_or_404(Import, pk=object_id)
        response = HttpResponse(failed_rows_csv(import_run), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="import-{import_run.pk}-failed-rows.csv"'
        return response
