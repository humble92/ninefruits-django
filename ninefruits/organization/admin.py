"""Org unit types, org units and programs in the admin panel (original Filament
``Resources/Reference/{OrgUnitTypes,OrgUnits,Programs}``).

Org units have validity periods and are not deleted after use: a reorganization ends them and
links successors (the Reorganize action on the change page, ``ReorganizeOrgUnit``)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, ClassVar

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.admin import TabularInline
from unfold.decorators import action, display
from unfold.forms import BaseDialogForm
from unfold.widgets import (
    UnfoldAdminDateWidget,
    UnfoldAdminSelectMultipleWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextareaWidget,
)

from ninefruits.adminpanel.mixins import CatalogPermissionMixin
from ninefruits.institution.admin_support import ReferenceAdmin, admin_url, show_errors
from ninefruits.organization.actions import ReorganizeOrgUnit
from ninefruits.organization.enums import DegreeLevel, OrgUnitChangeType
from ninefruits.organization.models import OrgUnit, OrgUnitSuccession, OrgUnitType, Program
from ninefruits.security.enums import Permission


def unit_choices(except_pk: Any = None) -> list[tuple[int, str]]:
    """Every unit except the given one, labelled "code name" (original ``unitOptions``)."""
    units = OrgUnit.objects.order_by("code")
    if except_pk is not None:
        units = units.exclude(pk=except_pk)
    return [(unit.pk, str(unit)) for unit in units]


class EffectivePeriodForm(forms.ModelForm):  # type: ignore[type-arg]
    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        start, end = cleaned.get("effective_start_date"), cleaned.get("effective_end_date")
        if start and end and end < start:
            self.add_error(
                "effective_end_date",
                _("The %(attribute)s field must be a date after or equal to %(date)s.")
                % {"attribute": _("Valid until"), "date": _("Valid from")},
            )
        return cleaned


@admin.register(OrgUnitType)
class OrgUnitTypeAdmin(ReferenceAdmin):
    manage_permission = Permission.ORG_UNITS_MANAGE
    navigation_icon = "layers"
    navigation_order = 21
    fields = ("code", "name", "is_academic", "sort_order")
    list_display = ("code", "name_column", "is_academic", "sort_order")
    search_fields = ("code",)
    ordering = ("sort_order", "code")

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: OrgUnitType) -> str:
        return str(obj.name or "")


class CurrentOnlyFilter(admin.SimpleListFilter):
    """Valid today (default) or all units (original ``current`` filter, on by default)."""

    title = _("Currently valid only")
    parameter_name = "current"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, Any]]:
        return [("all", _("All"))]

    def choices(self, changelist: Any) -> Any:
        yield {
            "selected": self.value() is None,
            "query_string": changelist.get_query_string(remove=[self.parameter_name]),
            "display": _("Currently valid only"),
        }
        yield {
            "selected": self.value() == "all",
            "query_string": changelist.get_query_string({self.parameter_name: "all"}),
            "display": _("All"),
        }

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        if self.value() == "all":
            return queryset
        return queryset.effective_on(timezone.localdate())


class OrgUnitForm(EffectivePeriodForm):
    class Meta:
        model = OrgUnit
        fields = (
            "code",
            "org_unit_type",
            "name",
            "short_name",
            "parent",
            "effective_start_date",
            "effective_end_date",
            "sort_order",
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["org_unit_type"].queryset = OrgUnitType.objects.order_by("sort_order", "code")  # type: ignore[attr-defined]
        parents = OrgUnit.objects.order_by("code")
        if self.instance.pk:
            parents = parents.exclude(pk=self.instance.pk)
        self.fields["parent"].queryset = parents  # type: ignore[attr-defined]
        if not self.instance.pk:
            self.fields["effective_start_date"].initial = timezone.localdate()


class SuccessionInline(CatalogPermissionMixin, TabularInline):
    """Units that took over from this one. Read only; recorded by the Reorganize action."""

    model = OrgUnitSuccession
    fk_name = "predecessor"
    extra = 0
    max_num = 0
    can_delete = False
    fields = ("successor_code", "successor_name", "change_type", "effective_date", "reason")
    readonly_fields = fields
    verbose_name = _("successor")
    verbose_name_plural = _("successors")
    permissions: ClassVar[dict[str, str]] = {"view": Permission.REFERENCE_DATA_VIEW}

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        return super().get_queryset(request).select_related("successor")

    @admin.display(description=_("Successor"))
    def successor_code(self, obj: OrgUnitSuccession) -> str:
        return obj.successor.code

    @admin.display(description=pgettext_lazy("reference", "Name"))
    def successor_name(self, obj: OrgUnitSuccession) -> str:
        return str(obj.successor.name or "")


class ReorganizeForm(BaseDialogForm):
    change_type = forms.ChoiceField(
        label=pgettext_lazy("reference", "Change"), choices=OrgUnitChangeType.choices, widget=UnfoldAdminSelectWidget
    )
    successors = forms.MultipleChoiceField(
        label=_("Successor"),
        widget=UnfoldAdminSelectMultipleWidget,
        help_text=_("Only a split can have several successors."),
    )
    effective_date = forms.DateField(
        label=pgettext_lazy("reference", "Effective date"),
        widget=UnfoldAdminDateWidget,
        help_text=_("The unit ends the day before this date; the successor takes over from this date."),
    )
    reason = forms.CharField(
        label=pgettext_lazy("common", "Reason"), max_length=1000, widget=UnfoldAdminTextareaWidget(attrs={"rows": 3})
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["successors"].choices = unit_choices(self.object_id)  # type: ignore[attr-defined]


@admin.register(OrgUnit)
class OrgUnitAdmin(ReferenceAdmin):
    """Org units with validity periods. Units are not deleted after use; a reorganization ends
    them and links successors."""

    manage_permission = Permission.ORG_UNITS_MANAGE
    import_type = "org_units"
    navigation_icon = "account_balance"
    navigation_order = 20
    form = OrgUnitForm
    list_display = (
        "code",
        "name_column",
        "type_column",
        "parent_column",
        "effective_start_date",
        "effective_end_date",
    )
    list_filter = ("org_unit_type", CurrentOnlyFilter)
    list_select_related = ("org_unit_type", "parent")
    search_fields = ("code",)
    ordering = ("code",)
    inlines = (SuccessionInline,)
    actions_detail = ("reorganize",)

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Units are ended by a reorganization, not deleted (the original had no delete)."""
        return False

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: OrgUnit) -> str:
        return str(obj.name or "")

    @display(description=_("Type"), label=True)
    def type_column(self, obj: OrgUnit) -> str:
        return str(obj.org_unit_type.name or obj.org_unit_type.code)

    @display(description=_("Parent"))
    def parent_column(self, obj: OrgUnit) -> str:
        return str(obj.parent.name) if obj.parent else "-"

    def has_reorganize_permission(self, request: HttpRequest, object_id: Any = None) -> bool:
        return bool(request.user.has_perm(Permission.ORG_UNITS_MANAGE))

    @action(
        description=_("Reorganize"),
        url_path="reorganize",
        permissions=["reorganize"],
        icon="swap_horiz",
        dialog={"title": _("Reorganize"), "form_class": ReorganizeForm},
    )
    def reorganize(self, request: HttpRequest, form: ReorganizeForm, object_id: Any) -> HttpResponse:
        unit = get_object_or_404(OrgUnit, pk=object_id)
        data = form.cleaned_data
        successors = list(OrgUnit.objects.filter(pk__in=[int(pk) for pk in data["successors"]]))
        try:
            ReorganizeOrgUnit()(
                unit, data["change_type"], successors, data["effective_date"], data["reason"], request.user
            )
        except ValidationError as error:
            show_errors(request, error)
        else:
            messages.success(request, _("Reorganization recorded."))
        return HttpResponseRedirect(admin_url(unit))


class ProgramForm(EffectivePeriodForm):
    class Meta:
        model = Program
        fields = (
            "code",
            "name",
            "degree_title",
            "degree_level",
            "org_unit",
            "standard_duration_years",
            "effective_start_date",
            "effective_end_date",
            "allows_second_major",
            "allows_minor",
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["org_unit"].queryset = OrgUnit.objects.order_by("code")  # type: ignore[attr-defined]
        self.fields["degree_level"].choices = DegreeLevel.choices  # type: ignore[attr-defined]
        if not self.instance.pk:
            self.fields["effective_start_date"].initial = timezone.localdate()

    def clean_standard_duration_years(self) -> Decimal | None:
        value = self.cleaned_data.get("standard_duration_years")
        if value is not None and not Decimal("0.5") <= value <= Decimal("10"):
            raise ValidationError(
                _("The %(attribute)s field must be between %(min)s and %(max)s.")
                % {"attribute": _("Standard duration (years)"), "min": "0.5", "max": "10"}
            )
        return value


@admin.register(Program)
class ProgramAdmin(ReferenceAdmin):
    manage_permission = Permission.PROGRAMS_MANAGE
    import_type = "programs"
    navigation_icon = "school"
    navigation_order = 22
    form = ProgramForm
    list_display = (
        "code",
        "name_column",
        "degree_level_column",
        "org_unit_column",
        "effective_start_date",
        "effective_end_date",
    )
    list_select_related = ("org_unit",)
    search_fields = ("code",)
    ordering = ("code",)

    @display(description=pgettext_lazy("reference", "Name"))
    def name_column(self, obj: Program) -> str:
        return str(obj.name or "")

    @display(description=_("Degree level"), label=True)
    def degree_level_column(self, obj: Program) -> str:
        return str(DegreeLevel(obj.degree_level).label)

    @display(description=_("Org unit"))
    def org_unit_column(self, obj: Program) -> str:
        return str(obj.org_unit.name or obj.org_unit.code)
