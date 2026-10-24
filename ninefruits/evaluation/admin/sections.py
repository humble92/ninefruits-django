"""Response rates per section for staff (original Filament ``SectionEvaluationResource``, legacy
counsel/academy_list.php). The results open the section's results page in the portal, which
shows the answers once the term's results are published."""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.contrib.admin.options import ActionLocation
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.decorators import action, display

from ninefruits.adminpanel.mixins import CatalogAdmin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.evaluation.models import EvaluationResponse, SectionEvaluation, TermEvaluation
from ninefruits.evaluation.services.results import rate
from ninefruits.organization.models import OrgUnit
from ninefruits.registration.admin.common import DefaultTermFilter, term_label
from ninefruits.term.models import Term

ACTIVE = ("enrolled", "completed")


class EvaluationTermFilter(DefaultTermFilter):
    """Terms with a course evaluation; the latest by default."""

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        terms = Term.objects.filter(pk__in=TermEvaluation.objects.values("term_id")).order_by("-start_date")
        return [("all", _("All")), *((str(term.pk), term_label(term)) for term in terms)]

    def value(self) -> Any:
        value = super(DefaultTermFilter, self).value()
        if value is None:
            latest = (
                TermEvaluation.objects.order_by("-term__start_date").values_list("term_id", flat=True).first()
                or super().value()
            )
            return str(latest) if latest is not None else None
        return value


class OfferingUnitFilter(admin.SimpleListFilter):
    title = _("Offering unit")
    parameter_name = "unit"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[Any, Any]]:
        return [(str(unit.pk), str(unit)) for unit in OrgUnit.objects.order_by("code")]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        return queryset.filter(org_unit_id=self.value()) if self.value() else queryset


@admin.register(SectionEvaluation)
class SectionEvaluationAdmin(CatalogAdmin):
    navigation_group = NavigationGroup.EVALUATION
    navigation_icon = "pie_chart"
    navigation_order = 30
    list_display = ("label", "title", "instructor_names", "responses", "rate_column")
    list_filter = (EvaluationTermFilter, OfferingUnitFilter)
    search_fields = ("course__code",)
    list_select_related = ("course", "version")
    ordering = ("course__code", "section_code")
    list_per_page = 50
    actions_row = ("results",)

    # -- access ----------------------------------------------------------------------------------
    def has_view_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return bool(request.user.has_perm("view_any", SectionEvaluation))

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

    def get_queryset(self, request: HttpRequest) -> Any:
        responses = (
            EvaluationResponse.objects.filter(section_id=OuterRef("pk"))
            .order_by()
            .values("section_id")
            .annotate(total=Count("*"))
            .values("total")
        )
        return (
            super()
            .get_queryset(request)
            .annotate(
                expected_count=Count(
                    "enrollments",
                    filter=Q(enrollments__status__in=ACTIVE, enrollments__version__requires_evaluation=True),
                ),
                responses_count=Coalesce(Subquery(responses, output_field=IntegerField()), 0),
            )
            .prefetch_related("instructor_assignments__instructor__person")
        )

    def get_search_results(self, request: HttpRequest, queryset: Any, search_term: str) -> tuple[Any, bool]:
        term = search_term.strip()
        if not term:
            return queryset, False
        return queryset.filter(course__code__istartswith=term), False

    # -- columns ---------------------------------------------------------------------------------
    @display(description=pgettext_lazy("offering", "Section"), ordering="course__code")
    def label(self, obj: SectionEvaluation) -> str:
        return obj.label()

    @display(description=pgettext_lazy("curriculum", "Title"))
    def title(self, obj: SectionEvaluation) -> str:
        return str(obj.version.title or "")

    @display(description=_("Instructors"))
    def instructor_names(self, obj: SectionEvaluation) -> str:
        names = [assignment.instructor.person.display_name() for assignment in obj.instructor_assignments.all()]
        return ", ".join(names) or "-"

    @display(description=_("Responses"), ordering="responses_count")
    def responses(self, obj: SectionEvaluation) -> str:
        return f"{int(getattr(obj, 'responses_count', 0))} / {int(getattr(obj, 'expected_count', 0))}"

    @display(description=_("Response rate"))
    def rate_column(self, obj: SectionEvaluation) -> str:
        expected = int(getattr(obj, "expected_count", 0))
        if expected == 0:
            return "-"
        return f"{rate(int(getattr(obj, 'responses_count', 0)), expected)}%"

    # -- actions ---------------------------------------------------------------------------------
    def has_results_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return self.has_view_permission(request)

    @action(
        description=pgettext_lazy("evaluation", "Results"),
        url_path="results",
        permissions=["results"],
        icon="bar_chart",
    )
    def results(self, request: HttpRequest, object_id: Any) -> HttpResponse:
        section = get_object_or_404(self.get_queryset(request), pk=object_id)
        return HttpResponseRedirect(reverse("portal:evaluation_results", args=[section.pk]))
