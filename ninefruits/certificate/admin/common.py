"""Shared pieces of the certificate admin screens: language choices, the issue dialog form
(original ``IssueCertificateAction`` schema) and the revoke form."""

from __future__ import annotations

from typing import Any

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy
from unfold.widgets import (
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextareaWidget,
    UnfoldAdminTextInputWidget,
)

from ninefruits.certificate.models import CertificateType

REASON_MAX = 1000


def supported_locales() -> list[str]:
    """The installation's languages (institution settings), English when not set."""
    from ninefruits.settings.groups.base import MissingSettings
    from ninefruits.settings.groups.institution import InstitutionSettings

    try:
        locales = list(InstitutionSettings.load().supported_locales)
    except MissingSettings:
        locales = []
    return locales or [str(settings.LANGUAGE_CODE)]


def locale_choices() -> list[tuple[str, str]]:
    """``(code, "code · name")`` of the supported languages (the original showed the code)."""
    names = dict(settings.LANGUAGES)
    return [(code, f"{code} · {names[code]}" if code in names else code) for code in supported_locales()]


class IssueCertificateForm(forms.Form):
    certificate_type = forms.ModelChoiceField(
        label=pgettext_lazy("certificate", "Kind"),
        queryset=CertificateType.objects.none(),
        widget=UnfoldAdminSelectWidget,
    )
    locale = forms.ChoiceField(label=pgettext_lazy("common", "Language"), widget=UnfoldAdminSelectWidget)
    purpose = forms.CharField(label=_("Purpose"), max_length=200, required=False, widget=UnfoldAdminTextInputWidget)
    copies = forms.IntegerField(
        label=_("Copies"), min_value=1, max_value=20, initial=1, widget=UnfoldAdminIntegerFieldWidget
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        kinds = CertificateType.objects.filter(is_active=True).order_by("sort_order", "id")
        self.fields["certificate_type"].queryset = kinds  # type: ignore[attr-defined]
        self.fields["locale"].choices = locale_choices()  # type: ignore[attr-defined]
        from django.utils.translation import get_language

        current = get_language() or settings.LANGUAGE_CODE
        if current in supported_locales():
            self.initial.setdefault("locale", current)


class RevokeForm(forms.Form):
    reason = forms.CharField(
        label=pgettext_lazy("common", "Reason"),
        max_length=REASON_MAX,
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 3}),
    )


class ConfirmForm(forms.Form):
    """Nothing to enter: the page asks for confirmation (original ``requiresConfirmation``)."""
