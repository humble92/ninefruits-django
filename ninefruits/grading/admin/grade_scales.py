"""Grade scales in the admin panel (original Filament ``Resources/Reference/GradeScales`` with
``ItemsRelationManager``). Saving goes through ``SaveGradeScale``: the default scale is the
institution's scale, fixed at installation."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.contrib import admin
from django.db.models import Count
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.admin import TabularInline
from unfold.decorators import display

from ninefruits.adminpanel.mixins import CatalogPermissionMixin
from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.grading.actions import SaveGradeScale
from ninefruits.grading.models import GradeScale, GradeScaleItem
from ninefruits.institution.admin_support import ReferenceAdmin
from ninefruits.security.enums import Permission


class GradeScaleForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = GradeScale
        fields = ("code", "name", "max_grade_points", "is_default")
        help_texts = {
            "is_default": _(
                "The grade scale is fixed at installation: grades and GPAs are on it. It cannot be moved to another "
                "scale."
            )
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Set only while no scale is the default; never cleared or moved.
        self.fields["is_default"].disabled = GradeScale.objects.filter(is_default=True).exists()


class GradeScaleItemForm(forms.ModelForm):  # type: ignore[type-arg]
    scale: GradeScale | None = None

    class Meta:
        model = GradeScaleItem
        fields = (
            "code",
            "name",
            "grade_points",
            "min_percentage",
            "max_percentage",
            "counts_in_gpa",
            "is_passing",
            "applies_to",
            "sort_order",
        )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        points = cleaned.get("grade_points")
        if cleaned.get("counts_in_gpa") and points is None:
            self.add_error("grade_points", _("The %(attribute)s field is required.") % {"attribute": _("Grade points")})
        maximum = self.scale.max_grade_points if self.scale is not None else None
        if points is not None and maximum is not None and points > maximum:
            self.add_error(
                "grade_points",
                _("The %(attribute)s field must not be greater than %(max)s.")
                % {"attribute": _("Grade points"), "max": maximum},
            )
        low, high = cleaned.get("min_percentage"), cleaned.get("max_percentage")
        if low is not None and high is not None and high < low:
            self.add_error(
                "max_percentage",
                _("The %(attribute)s field must be greater than or equal to %(value)s.")
                % {"attribute": _("To (%)"), "value": _("From (%)")},
            )
        return cleaned


class GradeScaleItemInline(CatalogPermissionMixin, TabularInline):
    model = GradeScaleItem
    fk_name = "grade_scale"
    form = GradeScaleItemForm
    extra = 0
    verbose_name = _("grade")
    verbose_name_plural = _("grades")
    permissions: ClassVar[dict[str, str]] = {
        "view": Permission.REFERENCE_DATA_VIEW,
        "add": Permission.GRADE_SCALES_MANAGE,
        "change": Permission.GRADE_SCALES_MANAGE,
        "delete": Permission.GRADE_SCALES_MANAGE,
    }

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return self._allowed(request, "add")

    def get_formset(self, request: HttpRequest, obj: Any = None, **kwargs: Any) -> Any:
        kwargs["form"] = type("GradeScaleItemForm", (self.form,), {"scale": obj})
        return super().get_formset(request, obj, **kwargs)


@admin.register(GradeScale)
class GradeScaleAdmin(ReferenceAdmin):
    manage_permission = Permission.GRADE_SCALES_MANAGE
    navigation_group = NavigationGroup.REFERENCE_DATA
    navigation_icon = "bar_chart"
    navigation_order = 61
    form = GradeScaleForm
    list_display = ("code", "name_column", "max_grade_points", "items_count", "is_default")
    search_fields = ("code",)
    ordering = ("code",)
    inlines = (GradeScaleItemInline,)

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).annotate(item_total=Count("items"))

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        if obj is not None and obj.is_default:
            return False
        return super().has_delete_permission(request, obj)

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: GradeScale) -> str:
        return str(obj.name or "")

    @display(description=pgettext_lazy("reference", "Grades"), ordering="item_total")
    def items_count(self, obj: GradeScale) -> int:
        return int(getattr(obj, "item_total", 0))

    def save_model(self, request: HttpRequest, obj: GradeScale, form: Any, change: bool) -> None:
        attributes = {
            name: form.cleaned_data[name] for name in ("code", "name", "max_grade_points") if name in form.cleaned_data
        }
        if not form.fields["is_default"].disabled:
            attributes["is_default"] = form.cleaned_data.get("is_default", False)
        # The default flag is disabled once a default exists, so SaveGradeScale accepts the values.
        target = GradeScale.objects.get(pk=obj.pk) if change else None
        saved = SaveGradeScale()(target, attributes)
        obj.pk = saved.pk
        obj._state.adding = False
