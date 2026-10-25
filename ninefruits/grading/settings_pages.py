"""Grading policy page (original ``App\\Filament\\Admin\\Pages\\ManageGradingSettings``): GPA
precision, retakes, grade caps for relative evaluation, academic standing and honors. The grade
scale itself is fixed at installation and only shown. Changes apply to calculations from now on;
recalculate term records to apply them to past terms."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from django import forms
from django.utils.translation import gettext, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from unfold.widgets import (
    UnfoldAdminDecimalFieldWidget,
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextInputWidget,
    UnfoldBooleanSwitchWidget,
)

from ninefruits.grading.enums import GpaRounding, RetakePolicy
from ninefruits.grading.settings import GradingSettings
from ninefruits.security.enums import Permission
from ninefruits.settings.admin_views import Section, SettingsPage, register_settings_page

CAP_PATTERN = re.compile(r"^\s*([A-Za-z])\s*[=:]\s*(\d{1,3})\s*$")


def parse_caps(text: str) -> dict[str, int]:
    """``"A=30, B=40"`` -> ``{"A": 30, "B": 40}``."""
    caps: dict[str, int] = {}
    for part in re.split(r"[,\n;]+", text or ""):
        if not part.strip():
            continue
        match = CAP_PATTERN.match(part)
        if match is None:
            raise forms.ValidationError(gettext("Write each cap as a letter and a percentage, e.g. A=30, B=40."))
        group, cap = match.group(1).upper(), int(match.group(2))
        if cap > 100:
            raise forms.ValidationError(
                gettext("The %(attribute)s field must not be greater than %(max)s.")
                % {"attribute": gettext("Cap"), "max": 100}
            )
        caps[group] = cap
    return caps


def format_caps(caps: dict[str, int]) -> str:
    return ", ".join(f"{group}={cap}" for group, cap in sorted((caps or {}).items()))


def default_scale_name() -> str:
    from ninefruits.grading.models import GradeScale

    scale = GradeScale.objects.filter(is_default=True).first()
    return str(scale.name) if scale is not None else "-"


def retake_grade_choices() -> list[tuple[str, str]]:
    from ninefruits.grading.models import GradeScaleItem

    codes = (
        GradeScaleItem.objects.filter(grade_scale__is_default=True, grade_points__isnull=False)
        .order_by("sort_order", "id")
        .values_list("code", flat=True)
    )
    return [("", str(_("No cap"))), *((code, code) for code in codes)]


class GradingSettingsForm(forms.Form):
    gpa_decimals = forms.IntegerField(
        label=_("Decimals"), min_value=0, max_value=3, widget=UnfoldAdminIntegerFieldWidget
    )
    gpa_rounding = forms.ChoiceField(label=_("Rounding"), choices=GpaRounding.choices, widget=UnfoldAdminSelectWidget)
    retake_policy = forms.ChoiceField(
        label=_("Retakes in the cumulative GPA"),
        choices=RetakePolicy.choices,
        widget=UnfoldAdminSelectWidget,
        help_text=_("Term GPAs always keep every grade of their term."),
    )
    retake_max_grade = forms.ChoiceField(
        label=_("Highest grade for a retake"),
        required=False,
        widget=UnfoldAdminSelectWidget,
        help_text=_("Grades above it cannot be given to a retake."),
    )
    relative_grade_caps = forms.CharField(
        label=_("Grade caps"),
        required=False,
        max_length=200,
        widget=UnfoldAdminTextInputWidget(attrs={"placeholder": "A=30, B=40"}),
        help_text=_(
            "The most a grade group (the letter: A for A+, A0, A-) may take of a section's graded students. Groups "
            "without a cap are free."
        ),
    )
    relative_cap_tolerance_percent = forms.IntegerField(
        label=_("Tolerance above the cap"), min_value=0, max_value=20, widget=UnfoldAdminIntegerFieldWidget
    )
    relative_minimum_students = forms.IntegerField(
        label=_("Check from this many graded students"),
        min_value=0,
        max_value=200,
        widget=UnfoldAdminIntegerFieldWidget,
        help_text=_("Smaller sections are not checked against the caps."),
    )
    warning_gpa_below = forms.DecimalField(
        label=_("Warning when the term GPA is below"),
        min_value=Decimal(0),
        max_value=Decimal(5),
        decimal_places=3,
        widget=UnfoldAdminDecimalFieldWidget,
        help_text=_("A term with only pass/fail courses gives no warning."),
    )
    standing_regular_terms_only = forms.BooleanField(
        label=_("Judge only regular terms (not summer or winter)"), required=False, widget=UnfoldBooleanSwitchWidget
    )
    dismissal_warning_count = forms.IntegerField(
        label=_("Warnings for dismissal review"),
        min_value=0,
        max_value=10,
        widget=UnfoldAdminIntegerFieldWidget,
        help_text=_("0 turns it off. The student is flagged for review; dismissal is a status change."),
    )
    dismissal_consecutive_only = forms.BooleanField(
        label=_("Count only consecutive warnings"), required=False, widget=UnfoldBooleanSwitchWidget
    )
    honors_min_gpa = forms.DecimalField(
        label=_("Minimum term GPA"),
        min_value=Decimal(0),
        max_value=Decimal(5),
        decimal_places=3,
        widget=UnfoldAdminDecimalFieldWidget,
    )
    honors_min_credits = forms.DecimalField(
        label=_("Minimum GPA credits in the term"),
        min_value=Decimal(0),
        max_value=Decimal(40),
        decimal_places=1,
        widget=UnfoldAdminDecimalFieldWidget,
    )
    honors_exclude_failing = forms.BooleanField(
        label=_("No honors with a failed course"), required=False, widget=UnfoldBooleanSwitchWidget
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["retake_max_grade"].choices = retake_grade_choices()  # type: ignore[attr-defined]

    def clean_relative_grade_caps(self) -> dict[str, int]:
        return parse_caps(self.cleaned_data.get("relative_grade_caps") or "")


@register_settings_page
class ManageGradingSettings(SettingsPage):
    settings_class = GradingSettings
    permission = Permission.GRADING_POLICIES_MANAGE
    slug = "grading"
    title = _("Grading policy")
    icon = "calculate"
    order = 50
    form_class = GradingSettingsForm

    @property
    def sections(self) -> list[Section]:  # type: ignore[override]
        return [
            Section(
                _("Grade scale"),
                [],
                description=gettext("Grade scale: %(scale)s (fixed at installation).")
                % {"scale": default_scale_name()},
            ),
            Section(_("GPA"), ["gpa_decimals", "gpa_rounding", "retake_policy", "retake_max_grade"]),
            Section(
                _("Relative evaluation"),
                ["relative_grade_caps", "relative_cap_tolerance_percent", "relative_minimum_students"],
            ),
            Section(
                _("Academic standing"),
                [
                    "warning_gpa_below",
                    "standing_regular_terms_only",
                    "dismissal_warning_count",
                    "dismissal_consecutive_only",
                ],
            ),
            Section(
                pgettext_lazy("grading", "Honors"), ["honors_min_gpa", "honors_min_credits", "honors_exclude_failing"]
            ),
        ]

    def initial_from_settings(self, settings: Any) -> dict[str, Any]:
        data = super().initial_from_settings(settings)
        data["relative_grade_caps"] = format_caps(data.get("relative_grade_caps") or {})
        data["retake_max_grade"] = data.get("retake_max_grade") or ""
        return data

    def settings_data_from_form(self, cleaned_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "relative_grade_caps": dict(cleaned_data["relative_grade_caps"]),
            "relative_cap_tolerance_percent": int(cleaned_data["relative_cap_tolerance_percent"]),
            "relative_minimum_students": int(cleaned_data["relative_minimum_students"]),
            "gpa_decimals": int(cleaned_data["gpa_decimals"]),
            "gpa_rounding": str(cleaned_data["gpa_rounding"]),
            "retake_policy": str(cleaned_data["retake_policy"]),
            "retake_max_grade": cleaned_data.get("retake_max_grade") or None,
            "standing_regular_terms_only": bool(cleaned_data.get("standing_regular_terms_only")),
            "warning_gpa_below": float(cleaned_data["warning_gpa_below"]),
            "dismissal_warning_count": int(cleaned_data["dismissal_warning_count"]),
            "dismissal_consecutive_only": bool(cleaned_data.get("dismissal_consecutive_only")),
            "honors_min_gpa": float(cleaned_data["honors_min_gpa"]),
            "honors_min_credits": float(cleaned_data["honors_min_credits"]),
            "honors_exclude_failing": bool(cleaned_data.get("honors_exclude_failing")),
        }
