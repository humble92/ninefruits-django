"""Form fields for a ``TargetCriteria`` value (original ``App\\Filament\\Admin\\Support\\TargetCriteriaFields``):
term windows now; section eligibility and exclusion and seat groups later.

A ModelForm subclasses :class:`TargetCriteriaForm` and names the model field in
``criteria_field``; the inputs are ``<field>__year_levels``, ``<field>__admission_year_from`` ...
(declared for the default name ``eligibility``; :func:`criteria_fields` builds them for others)."""

from __future__ import annotations

from typing import Any, ClassVar

from django import forms
from django.utils import timezone
from django.utils.translation import gettext, pgettext
from django.utils.translation import gettext_lazy as _
from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultipleWidget,
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminSelectMultipleWidget,
)

from ninefruits.core.targeting import TargetCriteria
from ninefruits.grading.enums import AcademicStanding

PARTS = ("year_levels", "admission_year_from", "admission_year_to", "program_ids", "org_unit_ids", "academic_standings")


def criteria_fields(prefix: str = "eligibility") -> dict[str, forms.Field]:
    return {
        f"{prefix}__year_levels": forms.TypedMultipleChoiceField(
            label=_("Year levels"),
            required=False,
            coerce=int,
            choices=[(level, str(level)) for level in range(1, 7)],
            widget=UnfoldAdminCheckboxSelectMultipleWidget,
        ),
        f"{prefix}__admission_year_from": forms.IntegerField(
            label=_("Admitted from (year)"),
            required=False,
            min_value=1900,
            max_value=2200,
            widget=UnfoldAdminIntegerFieldWidget,
        ),
        f"{prefix}__admission_year_to": forms.IntegerField(
            label=_("Admitted until (year)"),
            required=False,
            min_value=1900,
            max_value=2200,
            widget=UnfoldAdminIntegerFieldWidget,
        ),
        f"{prefix}__program_ids": forms.TypedMultipleChoiceField(
            label=_("Programs"), required=False, coerce=int, widget=UnfoldAdminSelectMultipleWidget
        ),
        f"{prefix}__org_unit_ids": forms.TypedMultipleChoiceField(
            label=_("Org units"),
            required=False,
            coerce=int,
            help_text=_("Includes all units below the selected ones."),
            widget=UnfoldAdminSelectMultipleWidget,
        ),
        f"{prefix}__academic_standings": forms.MultipleChoiceField(
            label=_("Academic standing"),
            required=False,
            choices=AcademicStanding.choices,
            help_text=_("The standing from the latest term close. Leave empty for any."),
            widget=UnfoldAdminCheckboxSelectMultipleWidget,
        ),
    }


def _program_choices() -> list[tuple[int, str]]:
    from ninefruits.organization.models import Program

    return [
        (program.pk, str(program)) for program in Program.objects.effective_on(timezone.localdate()).order_by("code")
    ]


def _org_unit_choices() -> list[tuple[int, str]]:
    from ninefruits.organization.models import OrgUnit

    return [(unit.pk, str(unit)) for unit in OrgUnit.objects.order_by("code")]


class TargetCriteriaForm(forms.ModelForm):  # type: ignore[type-arg]
    criteria_field: ClassVar[str] = "eligibility"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        prefix = self.criteria_field
        self.fields[f"{prefix}__program_ids"].choices = _program_choices()  # type: ignore[attr-defined]
        self.fields[f"{prefix}__org_unit_ids"].choices = _org_unit_choices()  # type: ignore[attr-defined]
        if self.instance.pk:
            values = TargetCriteria.coerce(getattr(self.instance, prefix)).to_dict()
            for part in PARTS:
                self.initial.setdefault(f"{prefix}__{part}", values.get(part))

    def criteria(self) -> TargetCriteria:
        prefix = self.criteria_field
        return TargetCriteria.from_dict({part: self.cleaned_data.get(f"{prefix}__{part}") for part in PARTS})

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        prefix = self.criteria_field
        start, end = cleaned.get(f"{prefix}__admission_year_from"), cleaned.get(f"{prefix}__admission_year_to")
        if start is not None and end is not None and end < start:
            self.add_error(
                f"{prefix}__admission_year_to",
                gettext("The %(attribute)s field must be greater than or equal to %(value)s.")
                % {"attribute": _("Admitted until (year)"), "value": _("Admitted from (year)")},
            )
        return cleaned

    def _post_clean(self) -> None:
        super()._post_clean()  # type: ignore[misc]  # private Django API missing from django-stubs
        if not self.errors:
            setattr(self.instance, self.criteria_field, self.criteria())


for _name, _field in criteria_fields("eligibility").items():
    TargetCriteriaForm.declared_fields[_name] = _field
    TargetCriteriaForm.base_fields[_name] = _field


def criteria_summary(criteria: TargetCriteria) -> str:
    """A short description for tables, e.g. "Year levels 1, 2 · Admitted 2014~ · NURS"."""
    from ninefruits.organization.models import OrgUnit, Program

    if criteria.admission_year_from is not None and criteria.admission_year_to is not None:
        years: str | None = f"{criteria.admission_year_from}~{criteria.admission_year_to}"
    elif criteria.admission_year_from is not None:
        years = f"{criteria.admission_year_from}~"
    elif criteria.admission_year_to is not None:
        years = f"~{criteria.admission_year_to}"
    else:
        years = None
    parts = [
        f"{gettext('Year levels')} {', '.join(str(level) for level in criteria.year_levels)}"
        if criteria.year_levels
        else None,
        f"{pgettext('reference', 'Admitted')} {years}" if years else None,
        ", ".join(Program.objects.filter(pk__in=criteria.program_ids).order_by("code").values_list("code", flat=True))
        if criteria.program_ids
        else None,
        ", ".join(OrgUnit.objects.filter(pk__in=criteria.org_unit_ids).order_by("code").values_list("code", flat=True))
        if criteria.org_unit_ids
        else None,
        ", ".join(
            str(AcademicStanding(value).label) if value in AcademicStanding.values else value
            for value in criteria.academic_standings
        )
        if criteria.academic_standings
        else None,
    ]
    return " · ".join(part for part in parts if part)
