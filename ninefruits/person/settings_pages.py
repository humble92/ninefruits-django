"""Student record settings page (original ``App\\Filament\\Admin\\Pages\\ManageStudentRecordSettings``)."""

from __future__ import annotations

from typing import Any

from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminIntegerFieldWidget, UnfoldAdminTextInputWidget

from ninefruits.person.settings import StudentRecordSettings
from ninefruits.security.enums import Permission
from ninefruits.settings.admin_views import Section, SettingsPage, register_settings_page

PATTERN = r"^[^{}]*(\{(YYYY|YY)\}[^{}]*)*\{SEQ:\d{1,2}\}[^{}]*$"


def _integer(label: Any, minimum: int, maximum: int) -> forms.IntegerField:
    return forms.IntegerField(label=label, min_value=minimum, max_value=maximum, widget=UnfoldAdminIntegerFieldWidget)


class StudentRecordSettingsForm(forms.Form):
    student_number_pattern = forms.CharField(
        label=_("Student number pattern"),
        max_length=32,
        validators=[RegexValidator(PATTERN)],
        widget=UnfoldAdminTextInputWidget,
        help_text=_(
            "{YYYY} admission year, {YY} last two digits, {SEQ:n} sequence padded to n digits. "
            "Example: {YYYY}{SEQ:5} gives 202600001."
        ),
    )
    invitation_valid_days = _integer(_("Invitation links valid for (days)"), 1, 90)
    max_second_majors = _integer(_("Second majors at a time"), 0, 3)
    max_minors = _integer(_("Minors at a time"), 0, 3)


@register_settings_page
class ManageStudentRecordSettings(SettingsPage):
    settings_class = StudentRecordSettings
    permission = Permission.INSTITUTION_SETTINGS_MANAGE
    slug = "student-records"
    title = _("Student records")
    icon = "school"
    order = 40
    form_class = StudentRecordSettingsForm
    sections = (
        Section(
            "",
            ["student_number_pattern", "invitation_valid_days", "max_second_majors", "max_minors"],
        ),
    )

    def settings_data_from_form(self, cleaned_data: dict[str, Any]) -> dict[str, Any]:
        return {
            "student_number_pattern": str(cleaned_data["student_number_pattern"]),
            "invitation_valid_days": int(cleaned_data["invitation_valid_days"]),
            "max_second_majors": int(cleaned_data["max_second_majors"]),
            "max_minors": int(cleaned_data["max_minors"]),
        }
