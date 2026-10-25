"""Correction requests for published results (original Filament ``AssessmentCorrectionResource``):
approved (applied) or rejected by someone other than the requester, with
``assessments.manage``. Pending by default; the menu shows how many are pending."""

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
from ninefruits.assessment.actions import CorrectAssessmentResult
from ninefruits.assessment.enums import CorrectionStatus
from ninefruits.assessment.models import AssessmentResultCorrection
from ninefruits.grading.admin.common import DecisionForm, RequiredDecisionForm
from ninefruits.person.models import Person
from ninefruits.registration.admin.common import ChoiceFilter, ConfirmForm, run_form

STATUS_COLORS = {
    CorrectionStatus.PENDING.label: "warning",
    CorrectionStatus.APPROVED.label: "success",
    CorrectionStatus.REJECTED.label: "danger",
}


def describe(values: dict[str, Any] | None) -> str:
    """``LISTENING 25 · READING 20 = 85 · Passed`` (original ``describe``)."""
    data = values or {}
    parts = [f"{code} {score}" for code, score in dict(data.get("scores") or {}).items()]
    text = " · ".join(parts)
    if data.get("total") is not None:
        text += (" = " if text else "") + str(data["total"])
    if data.get("passed") is not None:
        text += " · " + (gettext("Passed") if data["passed"] else str(pgettext_lazy("assessment", "Not passed")))
    return text


class CorrectionStatusFilter(ChoiceFilter):
    title = pgettext_lazy("registration", "Status")
    parameter_name = "status"
    choices_class = CorrectionStatus
    default = CorrectionStatus.PENDING.value


@admin.register(AssessmentResultCorrection)
class AssessmentResultCorrectionAdmin(CatalogAdmin):
    navigation_group = NavigationGroup.ASSESSMENTS
    navigation_icon = "published_with_changes"
    navigation_order = 25
    list_display = (
        "requested_at",
        "session_column",
        "student_column",
        "previous_column",
        "proposed_column",
        "reason_short",
        "requested_by_email",
        "status_badge",
        "decision_column",
    )
    list_filter = (CorrectionStatusFilter,)
    list_select_related = (
        "result__student_record__person",
        "result__assessment_type",
        "result__session",
        "requested_by",
        "decided_by",
    )
    search_fields = ("result__student_record__student_number",)
    ordering = ("-requested_at", "-id")
    list_per_page = 50
    actions_row = ("approve_row", "reject_row", "cancel_row")

    # -- access ----------------------------------------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self.policy_allows(request, "view_any", AssessmentResultCorrection)

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
            queryset.filter(result__student_record__student_number__icontains=term)
            | queryset.filter(result__student_record__person__in=people),
            False,
        )

    def navigation_badge(self, request: HttpRequest) -> str | None:
        count = self.get_queryset(request).pending().count()
        return str(count) if count else None

    # -- columns ---------------------------------------------------------------------------------
    @display(description=pgettext_lazy("assessment", "Kind"))
    def session_column(self, obj: AssessmentResultCorrection) -> str:
        session = obj.result.session
        held = session.held_date.isoformat() if session is not None else str(obj.result.taken_date)
        return f"{held} · {obj.result.assessment_type.name}"

    @display(description=_("Student number"), ordering="result__student_record__student_number")
    def student_column(self, obj: AssessmentResultCorrection) -> str:
        record = obj.result.student_record
        return f"{record.student_number} {record.person.display_name()}"

    @display(description=_("Current values"))
    def previous_column(self, obj: AssessmentResultCorrection) -> str:
        return describe(obj.previous)

    @display(description=_("Proposed values"))
    def proposed_column(self, obj: AssessmentResultCorrection) -> str:
        return describe(obj.proposed)

    @display(description=pgettext_lazy("common", "Reason"))
    def reason_short(self, obj: AssessmentResultCorrection) -> str:
        return Truncator(obj.reason).chars(40)

    @display(description=pgettext_lazy("grading", "Requested by"))
    def requested_by_email(self, obj: AssessmentResultCorrection) -> str:
        return str(obj.requested_by.email)

    @display(description=pgettext_lazy("registration", "Status"), label=STATUS_COLORS)
    def status_badge(self, obj: AssessmentResultCorrection) -> str:
        return str(CorrectionStatus(obj.status).label)

    @display(description=pgettext_lazy("grading", "Note"))
    def decision_column(self, obj: AssessmentResultCorrection) -> str:
        if obj.decided_by is None:
            return Truncator(obj.decision_note).chars(40) if obj.decision_note else "-"
        note = f" · {Truncator(obj.decision_note).chars(40)}" if obj.decision_note else ""
        return f"{obj.decided_by.email}{note}"

    # -- buttons ---------------------------------------------------------------------------------
    def _correction(self, request: HttpRequest, object_id: Any) -> AssessmentResultCorrection:
        correction: AssessmentResultCorrection = get_object_or_404(
            self.get_queryset(request).select_related(
                "result__student_record", "result__assessment_type", "result__session"
            ),
            pk=object_id,
        )
        return correction

    def _changelist_url(self) -> str:
        return reverse("admin:assessment_assessmentresultcorrection_changelist")

    def _subtitle(self, correction: AssessmentResultCorrection) -> str:
        result = correction.result
        return (
            f"{result.student_record.student_number} · {result.assessment_type.name} · "
            f"{describe(correction.previous)} → {describe(correction.proposed)}"
        )

    def has_decide_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self.has_view_permission(request)

    @action(description=_("Approve"), url_path="approve", permissions=["decide"], icon="check")
    def approve_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        correction = self._correction(request, object_id)
        corrections = CorrectAssessmentResult()
        if not corrections.can_decide(correction, request.user):
            raise PermissionDenied
        form = DecisionForm(request.POST or None)

        def perform(form: Any) -> str:
            corrections.approve(correction, request.user, form.cleaned_data.get("note"))
            return gettext("Approved")

        return run_form(
            self, request, form, _("Approve"), self._changelist_url(), perform, subtitle=self._subtitle(correction)
        )

    @action(description=pgettext_lazy("grading", "Reject"), url_path="reject", permissions=["decide"], icon="close")
    def reject_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        correction = self._correction(request, object_id)
        corrections = CorrectAssessmentResult()
        if not corrections.can_decide(correction, request.user):
            raise PermissionDenied
        form = RequiredDecisionForm(request.POST or None)

        def perform(form: Any) -> str:
            corrections.reject(correction, request.user, form.cleaned_data["note"])
            return gettext("Rejected")

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("grading", "Reject"),
            self._changelist_url(),
            perform,
            subtitle=self._subtitle(correction),
        )

    @action(
        description=pgettext_lazy("grading", "Cancel request"), url_path="cancel", permissions=["decide"], icon="cancel"
    )
    def cancel_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        correction = self._correction(request, object_id)
        if correction.status != CorrectionStatus.PENDING or correction.requested_by_id != request.user.pk:
            raise PermissionDenied
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> None:
            CorrectAssessmentResult().cancel(correction, request.user)

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("grading", "Cancel request"),
            self._changelist_url(),
            perform,
            subtitle=self._subtitle(correction),
        )
