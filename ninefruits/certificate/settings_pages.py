"""Certificate settings page (original ``App\\Filament\\Admin\\Pages\\ManageCertificateSettings``):
serial number pattern, verification period and the default signer per language."""

from __future__ import annotations

from typing import Any

from django import forms
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from unfold.widgets import UnfoldAdminIntegerFieldWidget, UnfoldAdminTextInputWidget

from ninefruits.certificate.settings import SERIAL_PATTERN, CertificateSettings
from ninefruits.security.enums import Permission
from ninefruits.settings.admin_views import Section, SettingsPage, register_settings_page

SIGNER_PREFIX = "signer_"


def _locales() -> list[str]:
    from ninefruits.certificate.admin.common import supported_locales

    return supported_locales()


class CertificateSettingsForm(forms.Form):
    serial_pattern = forms.RegexField(
        label=_("Serial number pattern"),
        regex=SERIAL_PATTERN,
        max_length=64,
        widget=UnfoldAdminTextInputWidget,
        help_text=_(
            "Tokens: {TYPE} kind code, {YYYY} or {YY} year, {SEQ:6} sequence padded to 6 digits (required). The "
            "sequence restarts for each distinct prefix, so {TYPE}-{YYYY}-{SEQ:6} counts per kind and year."
        ),
    )
    verification_valid_days = forms.IntegerField(
        label=_("Verification valid for (days)"),
        min_value=0,
        max_value=3650,
        widget=UnfoldAdminIntegerFieldWidget,
        help_text=_("0 = always. After this many days the verification page reports the certificate as expired."),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for locale in _locales():
            self.fields[SIGNER_PREFIX + locale] = forms.CharField(
                label=gettext("Signer (%(locale)s)") % {"locale": locale},
                max_length=160,
                required=False,
                widget=UnfoldAdminTextInputWidget,
            )


@register_settings_page
class ManageCertificateSettings(SettingsPage):
    settings_class = CertificateSettings
    permission = Permission.CERTIFICATES_MANAGE
    slug = "certificates"
    title = _("Certificate settings")
    icon = "verified"
    order = 70
    form_class = CertificateSettingsForm

    @property
    def sections(self) -> list[Section]:  # type: ignore[override]
        return [
            Section("", ["serial_pattern", "verification_valid_days"]),
            Section(
                _("Signer by language"),
                [SIGNER_PREFIX + locale for locale in _locales()],
                description=_(
                    'Printed above the seal, e.g. "President, Ninefruits University". A template can override it.'
                ),
            ),
        ]

    def initial_from_settings(self, settings: Any) -> dict[str, Any]:
        data = super().initial_from_settings(settings)
        signers = data.pop("signer", {}) or {}
        for locale, signer in signers.items():
            data[SIGNER_PREFIX + locale] = signer
        return data

    def settings_data_from_form(self, cleaned_data: dict[str, Any]) -> dict[str, Any]:
        signers = {
            name.removeprefix(SIGNER_PREFIX): str(value).strip()
            for name, value in cleaned_data.items()
            if name.startswith(SIGNER_PREFIX) and str(value or "").strip()
        }
        return {
            "serial_pattern": str(cleaned_data["serial_pattern"]),
            "verification_valid_days": int(cleaned_data["verification_valid_days"]),
            "signer": signers,
        }
