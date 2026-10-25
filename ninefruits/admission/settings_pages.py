"""Admission settings page (original ``App\\Filament\\Admin\\Pages\\ManageAdmissionSettings``)."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.widgets import UnfoldAdminIntegerFieldWidget, UnfoldBooleanSwitchWidget

from ninefruits.admission.settings import AdmissionSettings
from ninefruits.security.enums import Permission
from ninefruits.settings.admin_views import Section, SettingsPage, register_settings_page


class AdmissionSettingsForm(forms.Form):
    applicant_registration_enabled = forms.BooleanField(
        label=_("Applicants can create an account"),
        required=False,
        widget=UnfoldBooleanSwitchWidget,
        help_text=_(
            'Shows "Create an account" on the sign-in and admissions pages. Turn off when you do not take '
            "online applications."
        ),
    )
    draft_expiry_days = forms.IntegerField(
        label=_("Expire untouched drafts after (days)"),
        min_value=1,
        max_value=730,
        widget=UnfoldAdminIntegerFieldWidget,
        help_text=_("Drafts in closed cycles expire regardless."),
    )
    max_document_size_mb = forms.IntegerField(
        label=_("Largest document (MB)"), min_value=1, max_value=50, widget=UnfoldAdminIntegerFieldWidget
    )


@register_settings_page
class ManageAdmissionSettings(SettingsPage):
    settings_class = AdmissionSettings
    permission = Permission.ADMISSION_CYCLES_MANAGE
    slug = "admissions"
    title = pgettext_lazy("admin", "Admissions")
    icon = "assignment"
    order = 45
    form_class = AdmissionSettingsForm
    sections = (Section("", ["applicant_registration_enabled", "draft_expiry_days", "max_document_size_mb"]),)

    def settings_data_from_form(self, cleaned_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "applicant_registration_enabled": bool(cleaned_data["applicant_registration_enabled"]),
            "draft_expiry_days": int(cleaned_data["draft_expiry_days"]),
            "max_document_size_mb": int(cleaned_data["max_document_size_mb"]),
        }
