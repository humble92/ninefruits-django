"""Graduation settings page (original ``App\\Filament\\Admin\\Pages\\ManageGraduationSettings``):
degree number pattern and the minimum cumulative GPA. Needs ``graduation.process``."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminDecimalFieldWidget, UnfoldAdminTextInputWidget

from ninefruits.graduation.settings import DEGREE_NUMBER_PATTERN, GraduationSettings
from ninefruits.security.enums import Permission
from ninefruits.settings.admin_views import SettingsPage, register_settings_page


class GraduationSettingsForm(forms.Form):
    degree_number_pattern = forms.RegexField(
        label=_("Degree number pattern"),
        regex=DEGREE_NUMBER_PATTERN,
        max_length=64,
        widget=UnfoldAdminTextInputWidget,
        help_text=_(
            "Tokens: {PROGRAM} program code, {YYYY} or {YY} graduation year, {SEQ:5} sequence per distinct prefix "
            "(required). Default {PROGRAM}-{YYYY}-{SEQ:5} → CS-2026-00001."
        ),
    )
    minimum_cumulative_gpa = forms.DecimalField(
        label=_("Minimum cumulative GPA"),
        required=False,
        min_value=Decimal("0"),
        max_value=Decimal("5"),
        decimal_places=2,
        widget=UnfoldAdminDecimalFieldWidget(attrs={"step": "0.01"}),
        help_text=_("Required to graduate (primary program). Leave empty for none."),
    )


@register_settings_page
class ManageGraduationSettings(SettingsPage):
    settings_class = GraduationSettings
    permission = Permission.GRADUATION_PROCESS
    slug = "graduation"
    title = _("Graduation settings")
    icon = "school"
    order = 75
    form_class = GraduationSettingsForm

    def settings_data_from_form(self, cleaned_data: dict[str, Any]) -> dict[str, Any]:
        gpa = cleaned_data.get("minimum_cumulative_gpa")
        return {
            "degree_number_pattern": str(cleaned_data["degree_number_pattern"]),
            "minimum_cumulative_gpa": None if gpa is None else float(gpa),
        }
