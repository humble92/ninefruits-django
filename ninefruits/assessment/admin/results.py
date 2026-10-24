"""Every examination result, from sessions and from outside bodies (original Filament
``AssessmentResultResource``): the ledger behind the "passed examination" graduation requirement
(legacy SSCORE_ADD, COMEXAM, CET rows). The list button **Record an external result** adds a
result with its evidence file; the row button **Remove** deletes one with a reason (not for
published session results)."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.contrib.admin.options import ActionLocation
from django.core.exceptions import PermissionDenied
from django.db.models import Exists, OuterRef, Prefetch
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.decorators import action, display

from ninefruits.adminpanel.mixins import CatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.assessment.actions import RecordAssessmentResult
from ninefruits.assessment.enums import ResultSource
from ninefruits.assessment.models import AssessmentComponentScore, AssessmentResult, format_score
from ninefruits.media.models import Media
from ninefruits.person.models import Person
from ninefruits.registration.admin.common import ReasonForm, run_form
from ninefruits.security.enums import Permission

from .common import TypeFilter
from .forms import ExternalResultForm
from .sessions import scores_text


class SourceFilter(admin.SimpleListFilter):
    title = pgettext_lazy("assessment", "Source")
    parameter_name = "source"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return list(ResultSource.choices)

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        return queryset.filter(source=self.value()) if self.value() else queryset


class PassedFilter(admin.SimpleListFilter):
    title = _("Passed")
    parameter_name = "passed"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [("yes", _("Yes")), ("no", _("No"))]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        if self.value() in ("yes", "no"):
            return queryset.filter(is_passed=self.value() == "yes")
        return queryset


@admin.register(AssessmentResult)
class AssessmentResultAdmin(CatalogAdmin):
    navigation_group = NavigationGroup.ASSESSMENTS
    navigation_icon = "fact_check"
    navigation_order = 20
    list_display = (
        "taken_date",
        "type_column",
        "student_number",
        "name",
        "total_column",
        "level_column",
        "passed_column",
        "certificate_column",
        "evidence_column",
    )
    list_filter = (TypeFilter, SourceFilter, PassedFilter)
    list_select_related = ("student_record__person", "assessment_type")
    search_fields = ("student_record__student_number",)
    ordering = ("-taken_date", "-id")
    list_per_page = 50
    actions_list = ("record_external",)
    actions_row = ("remove_row",)

    # -- access ----------------------------------------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(request.user.has_perm("view_any", AssessmentResult))

    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        evidence = Media.objects.filter(
            model_type="assessment.assessmentresult",
            model_id=OuterRef("pk"),
            collection_name=AssessmentResult.EVIDENCE_COLLECTION,
        )
        return (
            super()
            .get_queryset(request)
            .annotate(has_evidence_file=Exists(evidence))
            .prefetch_related(
                Prefetch(
                    "component_scores",
                    queryset=AssessmentComponentScore.objects.select_related("component").order_by(
                        "component__sort_order", "id"
                    ),
                )
            )
        )

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

    # -- columns ---------------------------------------------------------------------------------
    @display(description=pgettext_lazy("assessment", "Kind"))
    def type_column(self, obj: AssessmentResult) -> str:
        return f"{obj.assessment_type.name} ({ResultSource(obj.source).label})"

    @display(description=_("Student number"), ordering="student_record__student_number")
    def student_number(self, obj: AssessmentResult) -> str:
        return str(obj.student_record.student_number)

    @display(description=pgettext_lazy("people", "Name"))
    def name(self, obj: AssessmentResult) -> str:
        return str(obj.student_record.person.display_name())

    @display(description=_("Total"))
    def total_column(self, obj: AssessmentResult) -> str:
        total = format_score(obj.total_score) or "-"
        scores = scores_text(list(obj.component_scores.all()))
        return f"{total} ({scores})" if scores else total

    @display(description=_("Level"))
    def level_column(self, obj: AssessmentResult) -> str:
        return obj.level or "-"

    @display(description=_("Passed"), boolean=True)
    def passed_column(self, obj: AssessmentResult) -> bool:
        return bool(obj.is_passed)

    @display(description=_("Certificate number"))
    def certificate_column(self, obj: AssessmentResult) -> str:
        return obj.certificate_number or "-"

    @display(description=_("Evidence"))
    def evidence_column(self, obj: AssessmentResult) -> str:
        if not getattr(obj, "has_evidence_file", False):
            return "-"
        return format_html(
            '<a class="underline" href="{}" target="_blank" rel="noopener">{}</a>',
            reverse("assessment:evidence", args=[obj.pk]),
            gettext("Evidence"),
        )

    # -- buttons ---------------------------------------------------------------------------------
    def has_record_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return bool(request.user.has_perm(Permission.ASSESSMENTS_RECORD))

    def _changelist_url(self) -> str:
        return reverse("admin:assessment_assessmentresult_changelist")

    @action(
        description=_("Record an external result"),
        url_path="record-external",
        permissions=["record"],
        icon="upload_file",
    )
    def record_external(self, request: HttpRequest) -> HttpResponse:
        form = ExternalResultForm(request.POST or None, request.FILES or None, user=request.user)

        def perform(form: Any) -> str:
            data = form.cleaned_data
            RecordAssessmentResult().external(
                data["student_number"],
                data["assessment_type"],
                data["taken_date"],
                data["passed"] == "1",
                request.user,
                data.get("total"),
                data.get("level"),
                data.get("certificate_number"),
                data.get("note"),
                data.get("evidence"),
            )
            return gettext("Record an external result")

        return run_form(self, request, form, _("Record an external result"), self._changelist_url(), perform)

    @action(description=pgettext_lazy("assessment", "Remove"), url_path="remove", permissions=["record"], icon="delete")
    def remove_row(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        result = get_object_or_404(
            self.get_queryset(request).select_related("student_record", "assessment_type"), pk=object_id
        )
        if not self.has_record_permission(request):
            raise PermissionDenied
        form = ReasonForm(request.POST or None)

        def perform(form: Any) -> str:
            RecordAssessmentResult().remove(result, request.user, form.cleaned_data["reason"])
            return str(pgettext_lazy("assessment", "Remove"))

        return run_form(
            self,
            request,
            form,
            pgettext_lazy("assessment", "Remove"),
            self._changelist_url(),
            perform,
            subtitle=f"{result.student_record.student_number} · {result.assessment_type.name} · {result.taken_date}",
        )
