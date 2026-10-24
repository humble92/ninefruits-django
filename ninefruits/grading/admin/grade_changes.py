"""Grade change requests (original Filament ``GradeChangeRequestResource``; legacy
aca1/student_scoreedit*, which changed grades directly). Requests of sections in the user's scope
and the user's own; someone other than the requester approves, and approval applies the change.
Pending by default; the menu shows how many are pending."""

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
from ninefruits.grading.actions import ManageGradeChanges
from ninefruits.grading.enums import GradeChangeStatus
from ninefruits.grading.models import GradeChangeRequest
from ninefruits.person.models import Person

from .common import ChoiceFilter, ConfirmForm, DecisionForm, RequiredDecisionForm, run_form

STATUS_COLORS = {
    GradeChangeStatus.PENDING.label: "warning",
    GradeChangeStatus.APPROVED.label: "success",
    GradeChangeStatus.REJECTED.label: "danger",
}


class ChangeStatusFilter(ChoiceFilter):
    title = pgettext_lazy("registration", "Status")
    parameter_name = "status"
    choices_class = GradeChangeStatus
    default = GradeChangeStatus.PENDING.value


@admin.register(GradeChangeRequest)
class GradeChangeRequestAdmin(CatalogAdmin):
    navigation_group = NavigationGroup.GRADING
    navigation_icon = "swap_horiz"
    navigation_order = 20
    list_display = (
        "requested_at",
        "student_number",
        "name",
        "section_label",
        "change",
        "reason_short",
        "requested_by_email",
        "status_badge",
        "decided",
    )
    list_filter = (ChangeStatusFilter,)
    search_fields = ("enrollment__student_record__student_number",)
    list_select_related = (
        "enrollment__student_record__person",
        "enrollment__section__course",
        "requested_by",
        "decided_by",
    )
    ordering = ("-requested_at", "-id")
    list_per_page = 50
    actions_row = ("approve_row", "reject_row", "cancel_row")

    # -- access ----------------------------------------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(request.user.has_perm("view_any", GradeChangeRequest))

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).in_scope_of(request.user)

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
            queryset.filter(enrollment__student_record__student_number__icontains=term)
            | queryset.filter(enrollment__student_record__person__in=people),
            False,
        )

    def navigation_badge(self, request: HttpRequest) -> str | None:
        count = self.get_queryset(request).pending().count()
        return str(count) if count else None

    # -- columns ---------------------------------------------------------------------------------
    @display(description=_("Student number"), ordering="enrollment__student_record__student_number")
    def student_number(self, obj: GradeChangeRequest) -> str:
        return str(obj.enrollment.student_record.student_number)

    @display(description=pgettext_lazy("people", "Name"))
    def name(self, obj: GradeChangeRequest) -> str:
        return str(obj.enrollment.student_record.person.display_name())

    @display(description=pgettext_lazy("offering", "Section"))
    def section_label(self, obj: GradeChangeRequest) -> str:
        return obj.enrollment.section.label()

    @display(description=pgettext_lazy("grading", "Change"))
    def change(self, obj: GradeChangeRequest) -> str:
        score = f" ({format(obj.to_score, 'f')})" if obj.to_score is not None else ""
        return f"{obj.from_grade_code or '-'} → {obj.to_grade_code}{score}"

    @display(description=pgettext_lazy("common", "Reason"))
    def reason_short(self, obj: GradeChangeRequest) -> str:
        return Truncator(obj.reason).chars(50)

    @display(description=pgettext_lazy("grading", "Requested by"))
    def requested_by_email(self, obj: GradeChangeRequest) -> str:
        return str(obj.requested_by.email)

    @display(description=pgettext_lazy("registration", "Status"), label=STATUS_COLORS)
    def status_badge(self, obj: GradeChangeRequest) -> str:
        return str(GradeChangeStatus(obj.status).label)

    @display(description=pgettext_lazy("grading", "Decided by"))
    def decided(self, obj: GradeChangeRequest) -> str:
        if obj.decided_by_id is None:
            return "-"
        note = f" · {Truncator(obj.decision_note).chars(40)}" if obj.decision_note else ""
        return f"{obj.decided_by.email}{note}"

    # -- actions ---------------------------------------------------------------------------------
    def _request(self, request: HttpRequest, object_id: Any) -> GradeChangeRequest:
        return get_object_or_404(
            self.get_queryset(request).select_related(
                "enrollment__section__course", "enrollment__student_record", "requested_by"
            ),
            pk=object_id,
        )

    def _changelist_url(self) -> str:
        return reverse("admin:grading_gradechangerequest_changelist")

    def _subtitle(self, change: GradeChangeRequest) -> str:
        return (
            f"{change.enrollment.student_record.student_number} · {change.enrollment.section.label()} · "
            f"{change.from_grade_code or '-'} → {change.to_grade_code}"
        )

    def has_decide_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self.has_view_permission(request)

    @action(description=_("Approve"), url_path="approve", permissions=["decide"], icon="check")
    def approve_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        change = self._request(request, object_id)
        changes = ManageGradeChanges()
        if not changes.can_decide(change, request.user):
            raise PermissionDenied
        form = DecisionForm(request.POST or None)

        def perform(form: Any) -> str:
            changes.approve(change, request.user, form.cleaned_data.get("note"))
            return gettext("Approved")

        return run_form(
            self,
            request,
            form,
            _("Approve"),
            self._changelist_url(),
            perform,
            subtitle=self._subtitle(change),
            description=_("The grade changes from %(from)s to %(to)s now, and the student's GPA is recalculated.")
            % {"from": change.from_grade_code or "-", "to": change.to_grade_code},
        )

    @action(description=pgettext_lazy("grading", "Reject"), url_path="reject", permissions=["decide"], icon="close")
    def reject_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        change = self._request(request, object_id)
        changes = ManageGradeChanges()
        if not changes.can_decide(change, request.user):
            raise PermissionDenied
        form = RequiredDecisionForm(request.POST or None)

        def perform(form: Any) -> str:
            changes.reject(change, request.user, form.cleaned_data["note"])
            return gettext("Rejected")

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("grading", "Reject"),
            self._changelist_url(),
            perform,
            subtitle=self._subtitle(change),
        )

    @action(
        description=pgettext_lazy("grading", "Cancel request"), url_path="cancel", permissions=["decide"], icon="cancel"
    )
    def cancel_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        change = self._request(request, object_id)
        if change.status != GradeChangeStatus.PENDING or change.requested_by_id != request.user.pk:
            raise PermissionDenied
        form = ConfirmForm(request.POST if request.method == "POST" else None)

        def perform(form: Any) -> None:
            ManageGradeChanges().cancel(change, request.user)

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("grading", "Cancel request"),
            self._changelist_url(),
            perform,
            subtitle=self._subtitle(change),
        )
