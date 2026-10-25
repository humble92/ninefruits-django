"""Institution settings page (original ``App\\Filament\\Admin\\Pages\\ManageInstitutionSettings``)."""

from __future__ import annotations

from typing import Any
from zoneinfo import available_timezones

from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.widgets import UnfoldAdminCheckboxSelectMultipleWidget, UnfoldAdminSelectWidget

from ninefruits.i18n.forms import TranslatableFormField
from ninefruits.i18n.translation import fallback_language
from ninefruits.institution.services.supported_locales import SupportedLocales, available_catalog_locales
from ninefruits.security.enums import Permission
from ninefruits.settings.admin_views import Section, SettingsPage, register_settings_page
from ninefruits.settings.groups.institution import InstitutionSettings


def _timezones() -> list[tuple[str, str]]:
    return [(name, name) for name in sorted(available_timezones() | {"UTC"})]


def _available_languages() -> list[tuple[str, str]]:
    return [(code, SupportedLocales.label(code)) for code in available_catalog_locales()]


class InstitutionSettingsForm(forms.Form):
    name = TranslatableFormField(label=_("Institution name"))
    timezone = forms.ChoiceField(label=_("Time zone"), widget=UnfoldAdminSelectWidget)
    supported_locales = forms.MultipleChoiceField(
        label=_("Offered languages"), widget=UnfoldAdminCheckboxSelectMultipleWidget
    )
    default_locale = forms.ChoiceField(label=_("Default language"), widget=UnfoldAdminSelectWidget)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        languages = _available_languages()
        self.fields["timezone"].choices = _timezones()  # type: ignore[attr-defined]
        self.fields["supported_locales"].choices = languages  # type: ignore[attr-defined]
        self.fields["default_locale"].choices = languages  # type: ignore[attr-defined]


@register_settings_page
class ManageInstitutionSettings(SettingsPage):
    settings_class = InstitutionSettings
    permission = Permission.INSTITUTION_SETTINGS_MANAGE
    slug = "institution"
    title = _("Institution")
    icon = "account_balance"
    order = 20
    form_class = InstitutionSettingsForm
    sections = (
        Section(pgettext_lazy("admin", "General"), ["name", "timezone"]),
        Section(
            _("Languages"),
            ["supported_locales", "default_locale"],
            description=_("Languages offered to users. A language appears here when its translation folder exists."),
        ),
    )

    def settings_data_from_form(self, cleaned_data: dict[str, Any]) -> dict[str, Any]:
        supported = list(cleaned_data["supported_locales"])
        default = cleaned_data["default_locale"]
        return {
            "name": cleaned_data["name"],
            "supported_locales": supported,
            "default_locale": default if default in supported else fallback_language(),
            "timezone": cleaned_data["timezone"],
        }
