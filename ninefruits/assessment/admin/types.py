"""Examination kinds and their areas (original Filament ``AssessmentTypeResource`` with the
``ComponentsRelationManager``; legacy CET_TYPE with fixed areas, SSCORE_ADD exam numbers,
COMEXAM types): the institution defines the areas and the pass rule per kind."""

from __future__ import annotations

from typing import Any, ClassVar

from django.contrib import admin
from django.db.models import Count
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.admin import StackedInline
from unfold.decorators import display

from ninefruits.adminpanel.mixins import CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.assessment.enums import AssessmentCategory, ScoringMethod
from ninefruits.assessment.models import AssessmentComponent, AssessmentType, format_score
from ninefruits.institution.admin_support import ReferenceAdmin
from ninefruits.security.enums import Permission

from .forms import AssessmentComponentForm, AssessmentComponentFormSet, AssessmentTypeForm

SETUP_PERMISSIONS: dict[str, str] = {
    "view": Permission.REFERENCE_DATA_VIEW,
    "add": Permission.ASSESSMENTS_MANAGE,
    "change": Permission.ASSESSMENTS_MANAGE,
    "delete": Permission.ASSESSMENTS_MANAGE,
}


class AssessmentComponentInline(CatalogPermissionMixin, StackedInline):
    """The scored areas of a kind. A kind without areas is scored by one total (or pass/fail)."""

    model = AssessmentComponent
    form = AssessmentComponentForm
    formset = AssessmentComponentFormSet
    extra = 0
    tab = True
    ordering = ("sort_order", "id")
    fields = (("code", "sort_order"), ("max_score", "min_score"), "name")
    verbose_name = _("Areas")
    verbose_name_plural = _("Areas")
    permissions: ClassVar[dict[str, str]] = SETUP_PERMISSIONS

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "add")


@admin.register(AssessmentType)
class AssessmentTypeAdmin(ReferenceAdmin):
    manage_permission = Permission.ASSESSMENTS_MANAGE
    navigation_group = NavigationGroup.ASSESSMENTS
    navigation_icon = "school"
    navigation_order = 30
    form = AssessmentTypeForm
    inlines = (AssessmentComponentInline,)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    ("code", "category"),
                    "name",
                    "scoring",
                    ("max_score", "pass_score"),
                    ("allows_external", "is_active"),
                    "sort_order",
                )
            },
        ),
    )
    list_display = (
        "code",
        "name_column",
        "category_column",
        "scoring_column",
        "pass_score_column",
        "components_column",
        "allows_external",
        "is_active",
    )
    search_fields = ("code",)
    ordering = ("sort_order", "code")

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(component_total=Count("components"))

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: AssessmentType) -> str:
        return str(obj.name or "")

    @display(description=_("Category"))
    def category_column(self, obj: AssessmentType) -> str:
        return str(AssessmentCategory(obj.category).label)

    @display(description=_("Scoring"))
    def scoring_column(self, obj: AssessmentType) -> str:
        return str(ScoringMethod(obj.scoring).label)

    @display(description=_("Pass score"))
    def pass_score_column(self, obj: AssessmentType) -> str:
        if obj.pass_score is None:
            return "-"
        maximum = f" / {format_score(obj.max_score)}" if obj.max_score is not None else ""
        return f"{format_score(obj.pass_score)}{maximum}"

    @display(description=_("Areas"), ordering="component_total")
    def components_column(self, obj: AssessmentType) -> int:
        return int(getattr(obj, "component_total", 0) or 0)
