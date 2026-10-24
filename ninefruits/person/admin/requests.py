"""Status change requests and second major / minor applications (original Filament
``StatusChangeResource`` and ``AdditionalProgramRequestResource``). Requests are decided from the
list (approve, reject with a note); approvers never decide requests they filed (separation of
duties, checked again in the actions)."""

from __future__ import annotations

from typing import Any, ClassVar

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.contrib.filters.admin import ChoicesDropdownFilter
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import BaseDialogForm

from ninefruits.adminpanel.mixins import ReadOnlyCatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.person.actions import DecideAdditionalProgramRequest, DecideStatusChange
from ninefruits.person.enums import (
    AdditionalProgramRequestStatus,
    AdditionalProgramRole,
    StatusChangeStatus,
    StudentStatus,
)
from ninefruits.person.models import AdditionalProgramRequest, StudentRecord, StudentStatusChange
from ninefruits.security.enums import Permission

from .common import admin_change_url, note_field, show_errors


class ApproveForm(BaseDialogForm):
    note = note_field(required=False)


class RejectForm(BaseDialogForm):
    note = note_field(required=True)


class DefaultStatusFilter(ChoicesDropdownFilter):
    """Status filter that shows pending requests unless another status is chosen."""

    def __init__(
        self, field: Any, request: HttpRequest, params: Any, model: Any, model_admin: Any, field_path: Any
    ) -> None:
        if field_path not in request.GET and f"{field_path}__exact" not in params:
            params = {**params, f"{field_path}__exact": [StatusChangeStatus.REQUESTED.value]}
        super().__init__(field, request, params, model, model_admin, field_path)


_BADGES = {
    StatusChangeStatus.REQUESTED: "warning",
    StatusChangeStatus.APPROVED: "success",
    StatusChangeStatus.REJECTED: "danger",
    StatusChangeStatus.CANCELLED: "info",
}


@admin.register(StudentStatusChange)
class StudentStatusChangeAdmin(ReadOnlyCatalogAdmin):
    """Queue of status change requests from students."""

    permissions: ClassVar[dict[str, str]] = {"view": Permission.STUDENT_RECORDS_VIEW}
    navigation_group = NavigationGroup.STUDENT_RECORDS
    navigation_icon = "move_to_inbox"
    navigation_order = 20
    list_display = (
        "record_link",
        "student_name",
        "requested_at",
        "type",
        "to_status_display",
        "effective_date",
        "status_badge",
        "short_reason",
        "requested_by_email",
        "decided_by_email",
    )
    list_filter = (("status", DefaultStatusFilter),)
    list_select_related = ("student_record__person", "type", "requested_by", "decided_by")
    search_fields = ("student_record__student_number",)
    ordering = ("-requested_at", "-id")
    actions_row = ("approve", "reject")

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is not None:
            return bool(request.user.has_perm("view", obj))
        return bool(request.user.has_perm("view_any", StudentStatusChange))

    @display(description=_("Student number"), ordering="student_record__student_number")
    def record_link(self, obj: StudentStatusChange) -> Any:
        return format_html(
            '<a class="underline" href="{}">{}</a>',
            admin_change_url(obj.student_record),
            obj.student_record.student_number,
        )

    @display(description=pgettext_lazy("people", "Name"))
    def student_name(self, obj: StudentStatusChange) -> str:
        return obj.student_record.person.display_name()

    @display(description=_("New status"))
    def to_status_display(self, obj: StudentStatusChange) -> str:
        return str(StudentStatus(obj.to_status).label)

    @display(description=_("Request status"), label={str(k.label): v for k, v in _BADGES.items()})
    def status_badge(self, obj: StudentStatusChange) -> str:
        return str(StatusChangeStatus(obj.status).label)

    @display(description=_("Reason"))
    def short_reason(self, obj: StudentStatusChange) -> str:
        return obj.reason if len(obj.reason) <= 40 else obj.reason[:40] + "..."

    @display(description=pgettext_lazy("people", "Requested by"))
    def requested_by_email(self, obj: StudentStatusChange) -> str:
        return obj.requested_by.email if obj.requested_by else "-"

    @display(description=pgettext_lazy("people", "Decided by"))
    def decided_by_email(self, obj: StudentStatusChange) -> str:
        return obj.decided_by.email if obj.decided_by else "-"

    def _change(self, request: HttpRequest, object_id: Any) -> StudentStatusChange:
        change = get_object_or_404(StudentStatusChange.objects.visible_to(request.user), pk=object_id)
        if change.status != StatusChangeStatus.REQUESTED or not request.user.has_perm("decide", change):
            raise PermissionDenied
        return change

    def has_decide_permission(self, request: HttpRequest) -> bool:
        return bool(request.user.has_perm(Permission.STUDENT_STATUS_CHANGES_APPROVE))

    @action(
        description=_("Approve"),
        url_path="approve",
        permissions=["decide"],
        icon="check",
        variant=ActionVariant.SUCCESS,
        dialog={"title": _("Approve"), "form_class": ApproveForm},
    )
    def approve(self, request: HttpRequest, form: ApproveForm, object_id: Any) -> HttpResponse:
        change = self._change(request, object_id)
        try:
            DecideStatusChange().approve(change, request.user, form.cleaned_data.get("note") or None)
        except ValidationError as error:
            show_errors(request, error)
        else:
            messages.success(request, _("Request approved."))
        return HttpResponseRedirect(reverse("admin:person_studentstatuschange_changelist"))

    @action(
        description=pgettext_lazy("people", "Reject"),
        url_path="reject",
        permissions=["decide"],
        icon="close",
        variant=ActionVariant.DANGER,
        dialog={"title": pgettext_lazy("people", "Reject"), "form_class": RejectForm},
    )
    def reject(self, request: HttpRequest, form: RejectForm, object_id: Any) -> HttpResponse:
        change = self._change(request, object_id)
        try:
            DecideStatusChange().reject(change, request.user, form.cleaned_data["note"])
        except ValidationError as error:
            show_errors(request, error)
        else:
            messages.success(request, _("Request rejected."))
        return HttpResponseRedirect(reverse("admin:person_studentstatuschange_changelist"))


_PROGRAM_BADGES = {
    AdditionalProgramRequestStatus.REQUESTED: "warning",
    AdditionalProgramRequestStatus.APPROVED: "success",
    AdditionalProgramRequestStatus.REJECTED: "danger",
    AdditionalProgramRequestStatus.CANCELLED: "info",
}


@admin.register(AdditionalProgramRequest)
class AdditionalProgramRequestAdmin(ReadOnlyCatalogAdmin):
    """Second major and minor applications. The target program's staff decide; the home
    department sees its students' applications."""

    permissions: ClassVar[dict[str, str]] = {"view": Permission.ADDITIONAL_PROGRAMS_APPROVE}
    navigation_group = NavigationGroup.STUDENT_RECORDS
    navigation_icon = "stacks"
    navigation_order = 25
    list_display = (
        "requested_at",
        "record_link",
        "student_name",
        "primary_program",
        "program",
        "role_display",
        "term",
        "short_statement",
        "status_badge",
    )
    list_filter = (("status", DefaultStatusFilter), ("role", ChoicesDropdownFilter))
    list_select_related = ("student_record__person", "student_record__program", "program", "term")
    ordering = ("requested_at", "id")
    actions_row = ("approve", "reject")

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(request.user.has_perm("view_any", AdditionalProgramRequest))

    @display(description=_("Student number"))
    def record_link(self, obj: AdditionalProgramRequest) -> Any:
        record = obj.student_record
        request = getattr(self, "_request", None)
        if request is not None and StudentRecord.objects.visible_to(request.user).filter(pk=record.pk).exists():
            return format_html('<a class="underline" href="{}">{}</a>', admin_change_url(record), record.student_number)
        return record.student_number

    def changelist_view(self, request: HttpRequest, extra_context: Any = None) -> Any:
        self._request = request
        return super().changelist_view(request, extra_context)

    @display(description=pgettext_lazy("people", "Name"))
    def student_name(self, obj: AdditionalProgramRequest) -> str:
        return obj.student_record.person.display_name()

    @display(description=pgettext_lazy("people", "Primary program"))
    def primary_program(self, obj: AdditionalProgramRequest) -> str:
        return str(obj.student_record.program)

    @display(description=pgettext_lazy("people", "Kind"), label=True)
    def role_display(self, obj: AdditionalProgramRequest) -> str:
        return str(AdditionalProgramRole(obj.role).label)

    @display(description=_("Statement"))
    def short_statement(self, obj: AdditionalProgramRequest) -> str:
        text = obj.statement or "-"
        return text if len(text) <= 40 else text[:40] + "..."

    @display(description=_("Request status"), label={str(k.label): v for k, v in _PROGRAM_BADGES.items()})
    def status_badge(self, obj: AdditionalProgramRequest) -> str:
        return str(AdditionalProgramRequestStatus(obj.status).label)

    def _request_for(self, request: HttpRequest, object_id: Any) -> AdditionalProgramRequest:
        application = get_object_or_404(AdditionalProgramRequest.objects.visible_to(request.user), pk=object_id)
        if not request.user.has_perm("decide", application):
            raise PermissionDenied
        return application

    def has_decide_permission(self, request: HttpRequest) -> bool:
        return bool(request.user.has_perm(Permission.ADDITIONAL_PROGRAMS_APPROVE))

    @action(
        description=_("Approve"),
        url_path="approve",
        permissions=["decide"],
        icon="check",
        variant=ActionVariant.SUCCESS,
        dialog={"title": _("Approve"), "form_class": ApproveForm},
    )
    def approve(self, request: HttpRequest, form: ApproveForm, object_id: Any) -> HttpResponse:
        application = self._request_for(request, object_id)
        try:
            DecideAdditionalProgramRequest().approve(application, request.user, form.cleaned_data.get("note") or None)
        except ValidationError as error:
            show_errors(request, error)
        else:
            messages.success(request, _("Request approved."))
        return HttpResponseRedirect(reverse("admin:person_additionalprogramrequest_changelist"))

    @action(
        description=pgettext_lazy("people", "Reject"),
        url_path="reject",
        permissions=["decide"],
        icon="close",
        variant=ActionVariant.DANGER,
        dialog={"title": pgettext_lazy("people", "Reject"), "form_class": RejectForm},
    )
    def reject(self, request: HttpRequest, form: RejectForm, object_id: Any) -> HttpResponse:
        application = self._request_for(request, object_id)
        try:
            DecideAdditionalProgramRequest().reject(application, request.user, form.cleaned_data["note"])
        except ValidationError as error:
            show_errors(request, error)
        else:
            messages.success(request, _("Request rejected."))
        return HttpResponseRedirect(reverse("admin:person_additionalprogramrequest_changelist"))
