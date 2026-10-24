"""Instructors' requests to change a section's evaluation method (original Filament
``EvaluationMethodRequestResource``), decided by the staff who schedule the section
(``sections.manage`` for the offering unit). Pending by default; the menu shows how many are
pending."""

from __future__ import annotations

from typing import Any

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
from ninefruits.grading.actions import ManageEvaluationMethodRequests
from ninefruits.grading.enums import EvaluationMethod, RequestStatus
from ninefruits.grading.models import EvaluationMethodRequest

from .common import ChoiceFilter, DecisionForm, RequiredDecisionForm, run_form

STATUS_COLORS = {
    RequestStatus.PENDING.label: "warning",
    RequestStatus.APPROVED.label: "success",
    RequestStatus.REJECTED.label: "danger",
}


class RequestStatusFilter(ChoiceFilter):
    title = pgettext_lazy("registration", "Status")
    parameter_name = "status"
    choices_class = RequestStatus
    default = RequestStatus.PENDING.value


class RequestedMethodFilter(ChoiceFilter):
    title = _("Evaluation")
    parameter_name = "requested_method"
    choices_class = EvaluationMethod


@admin.register(EvaluationMethodRequest)
class EvaluationMethodRequestAdmin(CatalogAdmin):
    navigation_group = NavigationGroup.GRADING
    navigation_icon = "balance"
    navigation_order = 15
    list_display = (
        "requested_at",
        "section_label",
        "change",
        "reason_short",
        "requested_by_email",
        "status_badge",
        "decided",
    )
    list_filter = (RequestStatusFilter, RequestedMethodFilter)
    list_select_related = ("section__course", "section__version", "requested_by", "decided_by")
    ordering = ("-requested_at", "-id")
    list_per_page = 50
    actions_row = ("approve_row", "reject_row")

    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(request.user.has_perm("view_any", EvaluationMethodRequest))

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

    def navigation_badge(self, request: HttpRequest) -> str | None:
        count = self.get_queryset(request).pending().count()
        return str(count) if count else None

    # -- columns ---------------------------------------------------------------------------------
    @display(description=pgettext_lazy("offering", "Section"))
    def section_label(self, obj: EvaluationMethodRequest) -> str:
        return f"{obj.section.label()} {obj.section.version.title or ''}".strip()

    @display(description=pgettext_lazy("grading", "Change"))
    def change(self, obj: EvaluationMethodRequest) -> str:
        return (
            f"{EvaluationMethod(obj.section.evaluation_method).label} → {EvaluationMethod(obj.requested_method).label}"
        )

    @display(description=pgettext_lazy("common", "Reason"))
    def reason_short(self, obj: EvaluationMethodRequest) -> str:
        return Truncator(obj.reason).chars(60)

    @display(description=pgettext_lazy("grading", "Requested by"))
    def requested_by_email(self, obj: EvaluationMethodRequest) -> str:
        return str(obj.requested_by.email)

    @display(description=pgettext_lazy("registration", "Status"), label=STATUS_COLORS)
    def status_badge(self, obj: EvaluationMethodRequest) -> str:
        return str(RequestStatus(obj.status).label)

    @display(description=pgettext_lazy("grading", "Decided by"))
    def decided(self, obj: EvaluationMethodRequest) -> str:
        if obj.decided_by_id is None:
            return "-"
        note = f" · {Truncator(obj.decision_note).chars(40)}" if obj.decision_note else ""
        return f"{obj.decided_by.email}{note}"

    # -- actions ---------------------------------------------------------------------------------
    def _request(self, request: HttpRequest, object_id: Any) -> EvaluationMethodRequest:
        return get_object_or_404(
            self.get_queryset(request).select_related("section__course", "section__version", "requested_by"),
            pk=object_id,
        )

    def _changelist_url(self) -> str:
        return reverse("admin:grading_evaluationmethodrequest_changelist")

    def has_decide_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self.has_view_permission(request)

    @action(description=_("Approve"), url_path="approve", permissions=["decide"], icon="check")
    def approve_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        method_request = self._request(request, object_id)
        requests = ManageEvaluationMethodRequests()
        if not requests.can_decide(method_request, request.user):
            raise PermissionDenied
        form = DecisionForm(request.POST or None)

        def perform(form: Any) -> str:
            cleared = requests.approve(method_request, request.user, form.cleaned_data.get("note"))
            return gettext("Approved. %(count)s draft grade(s) cleared.") % {"count": cleared}

        return run_form(
            self,
            request,
            form,
            _("Approve"),
            self._changelist_url(),
            perform,
            subtitle=self.section_label(method_request),
            description=_(
                "The section's evaluation method changes now. Draft grades entered under the old method are cleared; "
                "the instructor is told by email."
            ),
        )

    @action(description=pgettext_lazy("grading", "Reject"), url_path="reject", permissions=["decide"], icon="close")
    def reject_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        method_request = self._request(request, object_id)
        requests = ManageEvaluationMethodRequests()
        if not requests.can_decide(method_request, request.user):
            raise PermissionDenied
        form = RequiredDecisionForm(request.POST or None)

        def perform(form: Any) -> str:
            requests.reject(method_request, request.user, form.cleaned_data["note"])
            return gettext("Rejected")

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("grading", "Reject"),
            self._changelist_url(),
            perform,
            subtitle=self.section_label(method_request),
        )
