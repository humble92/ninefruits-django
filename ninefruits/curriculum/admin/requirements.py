"""Graduation requirements per program, role (primary, second major, minor) and catalog years
(original Filament ``Resources/Curriculum/Requirements``). Evaluated by the graduation audit."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.apps import apps
from django.contrib import admin
from django.db.models import Count
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.admin import StackedInline
from unfold.decorators import display
from unfold.widgets import UnfoldAdminSelectMultipleWidget

from ninefruits.adminpanel.mixins import CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.curriculum.enums import ProgramRole, RequirementKind
from ninefruits.curriculum.models import Course, CourseCategory, CurriculumRequirement, CurriculumRequirementSet
from ninefruits.institution.admin_support import ReferenceAdmin
from ninefruits.organization.models import Program
from ninefruits.security.enums import Permission

REQUIREMENT_PERMISSIONS: dict[str, str] = {
    "view": Permission.REFERENCE_DATA_VIEW,
    "add": Permission.CURRICULUM_MANAGE,
    "change": Permission.CURRICULUM_MANAGE,
    "delete": Permission.CURRICULUM_MANAGE,
}


def _year_validators() -> list[Any]:
    from django.core.validators import MaxValueValidator, MinValueValidator

    return [MinValueValidator(1950), MaxValueValidator(2200)]


class RequirementSetForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = CurriculumRequirementSet
        fields = ("program", "program_role", "total_credits", "catalog_year_from", "catalog_year_to", "name", "note")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["program"].queryset = Program.objects.order_by("code")  # type: ignore[attr-defined]
        for name in ("catalog_year_from", "catalog_year_to"):
            self.fields[name].validators.extend(_year_validators())

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        year_from, year_to = cleaned.get("catalog_year_from"), cleaned.get("catalog_year_to")
        if year_from is not None and year_to is not None and year_to < year_from:
            self.add_error(
                "catalog_year_to",
                _("The %(attribute)s field must be greater than or equal to %(value)s.")
                % {"attribute": _("Catalog year to"), "value": _("Catalog year from")},
            )
            return cleaned
        program, role = cleaned.get("program"), cleaned.get("program_role")
        if program is not None and role and year_from is not None:
            # The exclusion constraint decides; this explains overlaps before saving.
            others = CurriculumRequirementSet.objects.filter(program=program, program_role=role).overlapping(
                year_from, year_to
            )
            if self.instance.pk:
                others = others.exclude(pk=self.instance.pk)
            if others.exists():
                self.add_error(
                    "catalog_year_from",
                    _("These catalog years overlap another requirement set of the program and role."),
                )
        return cleaned


def _assessment_type_choices() -> list[tuple[Any, str]] | None:
    """Examination kinds (Phase 9). ``None`` until the assessment app has them."""
    try:
        model = apps.get_model("assessment", "AssessmentType")
    except LookupError:
        return None
    return [(row.pk, str(row)) for row in model._default_manager.filter(is_active=True).order_by("sort_order")]


class RequirementForm(forms.ModelForm):  # type: ignore[type-arg]
    course_ids = forms.ModelMultipleChoiceField(
        label=pgettext_lazy("curriculum", "courses"),
        queryset=Course.objects.none(),
        required=False,
        widget=UnfoldAdminSelectMultipleWidget,
    )

    class Meta:
        model = CurriculumRequirement
        fields = ("kind", "category", "assessment_type_id", "min_credits", "min_courses", "name", "sort_order")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = CourseCategory.objects.order_by("sort_order", "code")  # type: ignore[attr-defined]
        courses = self.fields["course_ids"]
        courses.queryset = Course.objects.order_by("code")  # type: ignore[attr-defined]
        courses.label_from_instance = lambda course: course.code  # type: ignore[attr-defined]
        if self.instance.pk:
            self.initial["course_ids"] = list(self.instance.courses.values_list("pk", flat=True))
        choices = _assessment_type_choices()
        if choices is None:
            self.fields["assessment_type_id"].widget = forms.HiddenInput()
        else:
            self.fields["assessment_type_id"] = forms.TypedChoiceField(
                label=_("Examination kind"),
                choices=[("", "-"), *choices],
                coerce=int,
                required=False,
                empty_value=None,
            )
        if "min_courses" in self.fields:
            from django.core.validators import MinValueValidator

            self.fields["min_courses"].validators.append(MinValueValidator(1))

    def clean(self) -> dict[str, Any]:
        """The database CHECK per kind, explained (original form visibility rules)."""
        cleaned = super().clean() or {}
        kind = cleaned.get("kind")
        required = _("The %(attribute)s field is required.")
        if kind == RequirementKind.CATEGORY_CREDITS:
            if cleaned.get("category") is None:
                self.add_error("category", required % {"attribute": _("Course category")})
            if cleaned.get("min_credits") is None:
                self.add_error("min_credits", required % {"attribute": pgettext_lazy("curriculum", "Minimum credits")})
            cleaned.update(assessment_type_id=None, min_courses=None, course_ids=[])
        elif kind == RequirementKind.REQUIRED_COURSES:
            cleaned.update(category=None, assessment_type_id=None, min_credits=None, min_courses=None)
        elif kind == RequirementKind.COURSE_GROUP:
            if cleaned.get("min_credits") is None and cleaned.get("min_courses") is None:
                self.add_error("min_credits", required % {"attribute": pgettext_lazy("curriculum", "Minimum credits")})
            cleaned.update(category=None, assessment_type_id=None)
        elif kind == RequirementKind.ASSESSMENT_PASS:
            if cleaned.get("assessment_type_id") is None:
                self.add_error("assessment_type_id", required % {"attribute": _("Examination kind")})
            cleaned.update(category=None, min_credits=None, min_courses=None, course_ids=[])
        return cleaned

    def _post_clean(self) -> None:
        for name in ("category", "assessment_type_id", "min_credits", "min_courses"):
            if name in self.cleaned_data:
                setattr(self.instance, name, self.cleaned_data[name])
        super()._post_clean()

    def save_courses(self) -> None:
        if self.instance.pk:
            self.instance.courses.set(self.cleaned_data.get("course_ids") or [])


class RequirementInline(CatalogPermissionMixin, StackedInline):  # type: ignore[misc]
    model = CurriculumRequirement
    fk_name = "requirement_set"
    form = RequirementForm
    extra = 0
    tab = True
    ordering = ("sort_order", "id")
    fields = (
        ("kind", "sort_order"),
        ("category", "assessment_type_id"),
        ("min_credits", "min_courses"),
        "course_ids",
        "name",
    )
    verbose_name = _("Requirements")
    verbose_name_plural = _("Requirements")
    permissions: ClassVar[dict[str, str]] = REQUIREMENT_PERMISSIONS

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "add")


class ProgramRoleFilter(admin.SimpleListFilter):
    title = _("Program role")
    parameter_name = "program_role"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, Any]]:
        return list(ProgramRole.choices)

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        return queryset.filter(program_role=self.value()) if self.value() else queryset


@admin.register(CurriculumRequirementSet)
class CurriculumRequirementSetAdmin(ReferenceAdmin):
    manage_permission = Permission.CURRICULUM_MANAGE
    navigation_group = NavigationGroup.CURRICULUM
    navigation_icon = "checklist"
    navigation_order = 20
    form = RequirementSetForm
    inlines = (RequirementInline,)
    list_display = (
        "program_column",
        "role_column",
        "catalog_year_from",
        "catalog_year_to",
        "name_column",
        "total_credits",
        "requirements_count",
    )
    list_filter = (ProgramRoleFilter,)
    list_select_related = ("program",)
    search_fields = ("program__code",)
    ordering = ("program__code", "program_role", "catalog_year_from")

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(requirement_total=Count("requirements"))

    def save_formset(self, request: HttpRequest, form: Any, formset: Any, change: bool) -> None:
        super().save_formset(request, form, formset, change)
        for inline_form in formset.forms:
            data = getattr(inline_form, "cleaned_data", None)
            if isinstance(inline_form, RequirementForm) and data and not data.get("DELETE"):
                inline_form.save_courses()

    @display(description=_("Programs"), ordering="program__code")
    def program_column(self, obj: CurriculumRequirementSet) -> str:
        return obj.program.code

    @display(description=_("Program role"), label=True)
    def role_column(self, obj: CurriculumRequirementSet) -> str:
        return str(ProgramRole(obj.program_role).label)

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: CurriculumRequirementSet) -> str:
        return str(obj.name or "")

    @display(description=_("Requirements"), ordering="requirement_total")
    def requirements_count(self, obj: CurriculumRequirementSet) -> int:
        return int(getattr(obj, "requirement_total", 0) or 0)
