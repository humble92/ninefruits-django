"""Course evaluation settings page (original ``App\\Filament\\Admin\\Pages\\ManageEvaluationSettings``):
hiding grades until the evaluation is done, refusing uniform answers, and the minimums a new
term's evaluation starts with."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.widgets import UnfoldAdminIntegerFieldWidget, UnfoldBooleanSwitchWidget

from ninefruits.evaluation.settings import EvaluationSettings
from ninefruits.security.enums import Permission
from ninefruits.settings.admin_views import Section, SettingsPage, register_settings_page


class EvaluationSettingsForm(forms.Form):
    grades_require_evaluation = forms.BooleanField(
        label=_("Hide a term's grades until its evaluation is done"),
        required=False,
        widget=UnfoldBooleanSwitchWidget,
        help_text=_("Only while the evaluation is open; the grades show when it closes."),
    )
    reject_uniform_answers = forms.BooleanField(
        label=_("Refuse the same answer to every question"),
        required=False,
        widget=UnfoldBooleanSwitchWidget,
        help_text=_("As the legacy refused all 1s or all 5s."),
    )
    minimum_responses = forms.IntegerField(
        label=_("Minimum responses"),
        min_value=0,
        max_value=100,
        widget=UnfoldAdminIntegerFieldWidget,
        help_text=_("Defaults for a new term's evaluation."),
    )
    minimum_response_percent = forms.IntegerField(
        label=_("Minimum response rate (%)"), min_value=0, max_value=100, widget=UnfoldAdminIntegerFieldWidget
    )


@register_settings_page
class ManageEvaluationSettings(SettingsPage):
    settings_class = EvaluationSettings
    permission = Permission.EVALUATIONS_MANAGE
    slug = "evaluation"
    title = pgettext_lazy("evaluation.settings", "Course evaluation")
    icon = "fact_check"
    order = 60
    form_class = EvaluationSettingsForm
    sections = [
        Section(
            "",
            ["grades_require_evaluation", "reject_uniform_answers", "minimum_responses", "minimum_response_percent"],
        )
    ]

    def settings_data_from_form(self, cleaned_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "grades_require_evaluation": bool(cleaned_data.get("grades_require_evaluation")),
            "reject_uniform_answers": bool(cleaned_data.get("reject_uniform_answers")),
            "minimum_responses": int(cleaned_data["minimum_responses"]),
            "minimum_response_percent": int(cleaned_data["minimum_response_percent"]),
        }
