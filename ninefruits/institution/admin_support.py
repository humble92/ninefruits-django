"""Shared behaviour of the reference data admin screens (original
``App\\Filament\\Admin\\Resources\\Reference\\ReferenceResource``, ``SafeDeleteAction`` and the
``ReferenceImporters`` import action).

- Anyone with ``reference_data.view`` can look; the resource's manage permission is needed to
  change (``manage_permission``).
- Translatable names are searched in every language (``util.i18n_search_text``).
- Deleting a row other records use explains instead of failing; such rows should be deactivated
  or ended instead.
- ``import_type`` adds an "Import CSV" button to the list (``reference_data.import`` unless the
  import type names another permission)."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.contrib import messages
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, Q, RestrictedError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action

from ninefruits.adminpanel.mixins import CatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.i18n.fields import I18nSearchText
from ninefruits.security.enums import Permission

IN_USE_TITLE = _("Still in use")
IN_USE_BODY = _("Other records refer to this one. Deactivate it or end its validity instead.")


def admin_url(obj: Any, view: str = "change") -> str:
    opts = obj._meta
    if view == "changelist":
        return reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
    return reverse(f"admin:{opts.app_label}_{opts.model_name}_{view}", args=[obj.pk])


def show_errors(request: HttpRequest, error: ValidationError) -> None:
    """Domain actions report problems as ``ValidationError`` with their own field names
    (original ``ShowsActionErrors``): shown as a message."""
    for message in error.messages:
        messages.error(request, message)


def render_action_form(
    model_admin: Any, request: HttpRequest, form: forms.Form, title: Any, back_url: str, **extra: Any
) -> HttpResponse:
    context = {
        **model_admin.admin_site.each_context(request),
        "title": title,
        "form": form,
        "opts": model_admin.model._meta,
        "back_url": back_url,
        **extra,
    }
    return render(request, "adminpanel/action_form.html", context)


class ImportCsvForm(forms.Form):
    file = forms.FileField(label=_("CSV file"), help_text=_("UTF-8 with a header row."))


class ReferenceAdmin(CatalogAdmin):
    #: Permission needed to create, change and delete (the original policy's).
    manage_permission: ClassVar[Permission]
    #: Translatable fields searched in every language.
    translated_search_fields: ClassVar[tuple[str, ...]] = ("name",)
    #: Import type of the list's "Import CSV" button (``ninefruits.importing.registry``).
    import_type: ClassVar[str | None] = None
    navigation_group = NavigationGroup.REFERENCE_DATA
    list_per_page = 50

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        manage = getattr(cls, "manage_permission", None)
        if manage is not None and "permissions" not in cls.__dict__:
            cls.permissions = {
                "view": Permission.REFERENCE_DATA_VIEW,
                "add": manage,
                "change": manage,
                "delete": manage,
            }
        if cls.import_type and "actions_list" not in cls.__dict__:
            cls.actions_list = ["import_csv"]

    # -- permissions ------------------------------------------------------------------------------
    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return self._allowed(request, "add")

    # -- list ---------------------------------------------------------------------------------------
    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        """No bulk delete (the original screens delete one row at a time, with an explanation)."""
        actions = super().get_actions(request, action_location)
        actions.pop("delete_selected", None)
        return actions

    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        queryset, may_have_duplicates = super().get_search_results(request, queryset, search_term)
        term = search_term.strip()
        if not term or not self.translated_search_fields:
            return queryset, may_have_duplicates
        base = self.get_queryset(request)
        condition = Q()
        annotations = {}
        for name in self.translated_search_fields:
            annotations[f"_search_{name}"] = I18nSearchText(name)
            condition |= Q(**{f"_search_{name}__icontains": term})
        matches = base.annotate(**annotations).filter(condition).values("pk")
        return queryset | base.filter(pk__in=matches), may_have_duplicates

    # -- safe delete --------------------------------------------------------------------------------
    def delete_view(self, request: HttpRequest, object_id: str, extra_context: dict[str, Any] | None = None) -> Any:
        obj = self.get_object(request, object_id)
        if obj is not None and self.has_delete_permission(request, obj):
            _deleted, _count, _perms, protected = self.get_deleted_objects([obj], request)
            if protected:
                return self._in_use(request, obj, protected)
        try:
            with transaction.atomic():
                return super().delete_view(request, object_id, extra_context)
        except (ProtectedError, RestrictedError, IntegrityError) as error:
            if isinstance(error, IntegrityError) and getattr(error.__cause__, "sqlstate", None) not in (
                "23503",
                "23001",
            ):
                raise
            return self._in_use(request, obj, [])

    def _in_use(self, request: HttpRequest, obj: Any, protected: list[Any]) -> HttpResponse:
        details = format_html_join(", ", "{}", ((str(item),) for item in protected[:5])) if protected else ""
        messages.error(request, f"{IN_USE_TITLE}: {IN_USE_BODY}" + (f" ({details})" if details else ""))
        return HttpResponseRedirect(admin_url(obj) if obj is not None else self._changelist_url())

    def _changelist_url(self) -> str:
        opts = self.model._meta
        return reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")

    # -- CSV import ---------------------------------------------------------------------------------
    def has_import_csv_permission(self, request: HttpRequest) -> bool:
        if not self.import_type:
            return False
        from ninefruits.importing.registry import permission_for

        return bool(request.user.has_perm(permission_for(self.import_type)))

    @action(description=_("Import CSV"), url_path="import-csv", permissions=["import_csv"], icon="upload_file")
    def import_csv(self, request: HttpRequest) -> HttpResponse:
        from ninefruits.importing.registry import resource_for
        from ninefruits.importing.services import check_header, read_csv, start_import, sync_max_rows

        if not self.import_type or (resource := resource_for(self.import_type)) is None:
            raise PermissionDenied
        form = ImportCsvForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            upload = form.cleaned_data["file"]
            data = upload.read()
            try:
                csv_file = read_csv(data)
            except UnicodeDecodeError:
                form.add_error("file", _("The file is not UTF-8 text."))
            else:
                header = check_header(resource, csv_file.headers)
                if header.missing:
                    form.add_error(
                        "file",
                        _("Missing required columns: %(columns)s.") % {"columns": ", ".join(header.missing)},
                    )
                else:
                    stored = _store_upload(upload.name, data)
                    import_run = start_import(
                        self.import_type,
                        request.user,
                        upload.name,
                        stored,
                        csv_file.rows,
                        queue=len(csv_file.rows) > sync_max_rows(),
                    )
                    _report_import(request, import_run, resource.label)
                    return HttpResponseRedirect(reverse("admin:importing_import_change", args=[import_run.pk]))
        columns = ", ".join(resource.column_names())
        required = ", ".join(resource.required_columns())
        return render_action_form(
            self,
            request,
            form,
            _("Import CSV"),
            self._changelist_url(),
            subtitle=self.model._meta.verbose_name_plural,
            description=resource.__doc__.strip().splitlines()[0] if resource.__doc__ else "",
            notes=[
                _("Columns: %(columns)s") % {"columns": columns},
                _("Required columns: %(columns)s") % {"columns": required},
                _(
                    "Rows are matched by code: importing the same file again updates instead of duplicating. "
                    "Empty translation cells keep existing translations."
                ),
            ],
        )


def _store_upload(name: str, data: bytes) -> str:
    import uuid

    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    from ninefruits.media.services import sanitize_file_name

    return default_storage.save(f"imports/{uuid.uuid4().hex}/{sanitize_file_name(name)}", ContentFile(data))


def _report_import(request: HttpRequest, import_run: Any, label: Any) -> None:
    from ninefruits.importing.admin import completion_message

    if import_run.completed_at is None:
        messages.info(
            request,
            _("Import #%(id)s queued (%(rows)s rows). This page shows the result when it is finished.")
            % {"id": import_run.pk, "rows": import_run.total_rows},
        )
        return
    level = messages.WARNING if import_run.failed_rows_count() else messages.SUCCESS
    messages.add_message(request, level, completion_message(import_run, label))
