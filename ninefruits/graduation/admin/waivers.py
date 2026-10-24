"""Requirement waivers (original Filament ``DegreeWaiverResource``): requested by one person,
approved or rejected by another, lifted with a reason. The audit counts approved ones only.
Pending by default; the menu shows how many are pending."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import admin
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.text import Truncator
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display

from ninefruits.adminpanel.mixins import CatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.grading.admin.common import DecisionForm, RequiredDecisionForm
from ninefruits.graduation.actions import WaiveRequirement
from ninefruits.graduation.enums import WaiverStatus
from ninefruits.graduation.models import DegreeRequirementWaiver
from ninefruits.person.models import Person
from ninefruits.registration.admin.common import ChoiceFilter, run_form

from .forms import reason_field, requirement_name

STATUS_COLORS = {
    WaiverStatus.PENDING.label: "warning",
    WaiverStatus.APPROVED.label: "success",
    WaiverStatus.REJECTED.label: "danger",
    WaiverStatus.LIFTED.label: "info",
}


class WaiverStatusFilter(ChoiceFilter):
    title = pgettext_lazy("registration", "Status")
    parameter_name = "status"
    choices_class = WaiverStatus
    default = WaiverStatus.PENDING.value


class LiftForm(forms.Form):
    reason = reason_field()


@admin.register(DegreeRequirementWaiver)
class DegreeRequirementWaiverAdmin(CatalogAdmin):
    navigation_group = NavigationGroup.GRADUATION
    navigation_icon = "verified_user"
    navigation_order = 20
    list_display = (
        "requested_at",
        "student_column",
        "requirement_column",
        "reason_short",
        "requested_by_email",
        "status_badge",
        "decided_by_email",
        "decision_short",
        "lift_short",
    )
    list_filter = (WaiverStatusFilter,)
    list_select_related = (
        "student_record__person",
        "requirement__assessment_type",
        "requested_by",
        "decided_by",
    )
    search_fields = ("student_record__student_number",)
    ordering = ("-requested_at", "-id")
    list_per_page = 50
    actions_row = ("approve_row", "reject_row", "lift_row")

    # -- access (original DegreeAuditPolicy) -------------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is not None:
            return bool(request.user.has_perm("view", obj))
        return bool(request.user.has_perm("view_any", DegreeRequirementWaiver))

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_actions(self, request: HttpRequest, action_location: Any = ActionLocation.CHANGE_LIST) -> dict[str, Any]:
        actions = super().get_actions(request, action_location)
        actions.pop("delete_selected", None)
        return actions

    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        people = Person.objects.search(term).values("pk")
        return (
            queryset.filter(student_record__student_number__icontains=term)
            | queryset.filter(student_record__person__in=people),
            False,
        )

    def navigation_badge(self, request: HttpRequest) -> str | None:
        count = self.get_queryset(request).pending().count()
        return str(count) if count else None

    # -- columns -----------------------------------------------------------------------------------
    @display(description=_("Student number"), ordering="student_record__student_number", header=True)
    def student_column(self, obj: DegreeRequirementWaiver) -> tuple[str, str]:
        return str(obj.student_record.student_number), obj.student_record.person.display_name()

    @display(description=_("Requirements"))
    def requirement_column(self, obj: DegreeRequirementWaiver) -> str:
        return requirement_name(obj.requirement)

    @display(description=pgettext_lazy("common", "Reason"))
    def reason_short(self, obj: DegreeRequirementWaiver) -> str:
        return Truncator(obj.reason).chars(50)

    @display(description=pgettext_lazy("grading", "Requested by"))
    def requested_by_email(self, obj: DegreeRequirementWaiver) -> str:
        return str(obj.requested_by.email) if obj.requested_by_id else "-"

    @display(description=pgettext_lazy("registration", "Status"), label=STATUS_COLORS)
    def status_badge(self, obj: DegreeRequirementWaiver) -> str:
        return str(WaiverStatus(obj.status).label)

    @display(description=pgettext_lazy("grading", "Decided by"))
    def decided_by_email(self, obj: DegreeRequirementWaiver) -> str:
        return str(obj.decided_by.email) if obj.decided_by_id else "-"

    @display(description=pgettext_lazy("grading", "Note"))
    def decision_short(self, obj: DegreeRequirementWaiver) -> str:
        return Truncator(obj.decision_note).chars(40) if obj.decision_note else "-"

    @display(description=_("Lift reason"))
    def lift_short(self, obj: DegreeRequirementWaiver) -> str:
        return Truncator(obj.lift_reason).chars(40) if obj.lift_reason else "-"

    # -- buttons -----------------------------------------------------------------------------------
    def _waiver(self, request: HttpRequest, object_id: Any) -> DegreeRequirementWaiver:
        return get_object_or_404(
            self.get_queryset(request).select_related("student_record", "requirement__assessment_type"),
            pk=object_id,
        )

    def _changelist_url(self) -> str:
        return reverse("admin:graduation_degreerequirementwaiver_changelist")

    @staticmethod
    def _subtitle(waiver: DegreeRequirementWaiver) -> str:
        return f"{waiver.student_record.student_number} · {requirement_name(waiver.requirement)} · {waiver.reason}"

    def has_decide_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self.has_view_permission(request)

    @action(description=_("Approve"), url_path="approve", permissions=["decide"], icon="check")
    def approve_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        waiver = self._waiver(request, object_id)
        waive = WaiveRequirement()
        if not waive.can_decide(waiver, request.user):
            raise PermissionDenied
        form = DecisionForm(request.POST or None)

        def perform(form: Any) -> str:
            waive.approve(waiver, request.user, form.cleaned_data.get("note"))
            return gettext("Approved")

        return run_form(
            self,
            request,
            form,
            _("Approve"),
            self._changelist_url(),
            perform,
            subtitle=self._subtitle(waiver),
        )

    @action(description=pgettext_lazy("grading", "Reject"), url_path="reject", permissions=["decide"], icon="close")
    def reject_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        waiver = self._waiver(request, object_id)
        waive = WaiveRequirement()
        if not waive.can_decide(waiver, request.user):
            raise PermissionDenied
        form = RequiredDecisionForm(request.POST or None)

        def perform(form: Any) -> str:
            waive.reject(waiver, request.user, form.cleaned_data["note"])
            return gettext("Rejected")

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("grading", "Reject"),
            self._changelist_url(),
            perform,
            subtitle=self._subtitle(waiver),
        )

    @action(description=_("Lift the waiver"), url_path="lift", permissions=["decide"], icon="undo")
    def lift_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        waiver = self._waiver(request, object_id)
        waive = WaiveRequirement()
        if not waive.can_lift(waiver, request.user):
            raise PermissionDenied
        form = LiftForm(request.POST or None)

        def perform(form: Any) -> str:
            waive.lift(waiver, request.user, form.cleaned_data["reason"])
            return gettext("Lifted")

        return run_form(
            self, request, form, _("Lift the waiver"), self._changelist_url(), perform, subtitle=self._subtitle(waiver)
        )
