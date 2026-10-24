"""Security and sign-in settings pages (original ``App\\Filament\\Admin\\Pages\\ManageSecuritySettings``
and ``ManageAuthenticationSettings``). Registered on import from ``ninefruits.security.admin``.

SSO client secrets are stored encrypted and never sent back to the browser; leaving the field
empty keeps the stored secret."""

from __future__ import annotations

import re
from typing import Any

from django import forms
from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _
from unfold.widgets import (
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminSelectMultipleWidget,
    UnfoldAdminSelectWidget,
    UnfoldBooleanSwitchWidget,
)

from ninefruits.security.crypto import encrypt_string
from ninefruits.security.enums import MfaEnforcement, Permission, SsoLinkMode, StudentNumberLogin
from ninefruits.settings.admin_views import Section, SettingsPage, register_settings_page
from ninefruits.settings.groups.authentication import AuthenticationSettings
from ninefruits.settings.groups.base import SettingsGroup
from ninefruits.settings.groups.security import SecuritySettings

_KEY = re.compile(r"^[a-z][a-z0-9-]*$")
PROVIDER_FIELDS = ("key", "label", "issuer", "client_id", "client_secret", "scopes", "trusts_mfa", "is_enabled")
DEFAULT_SCOPES = "openid email profile"


def _integer(label: Any, minimum: int, maximum: int, help_text: Any = "") -> forms.IntegerField:
    return forms.IntegerField(
        label=label, min_value=minimum, max_value=maximum, help_text=help_text, widget=UnfoldAdminIntegerFieldWidget
    )


# -- security ------------------------------------------------------------------------------------
class SecuritySettingsForm(forms.Form):
    mfa_enforcement = forms.ChoiceField(label=_("Policy"), widget=UnfoldAdminSelectWidget)
    mfa_required_role_ids = forms.TypedMultipleChoiceField(
        label=_("Roles that must use two-factor authentication"),
        required=False,
        coerce=int,
        widget=UnfoldAdminSelectMultipleWidget,
        help_text=_("Used when the policy is Required for selected roles."),
    )
    mfa_grace_period_days = _integer(
        _("Grace period (days)"),
        0,
        90,
        _("Days a user can keep working after the requirement first applies to them. 0 means immediately."),
    )
    mfa_remember_device_days = _integer(
        _("Remember devices for (days)"),
        0,
        365,
        _("Users can skip the code on a trusted device for this many days. 0 turns this off."),
    )
    mfa_email_code_enabled = forms.BooleanField(
        label=_("Allow email codes"),
        required=False,
        widget=UnfoldBooleanSwitchWidget,
        help_text=_(
            "Users can choose one-time codes by email instead of an authenticator app. Turning this off stops "
            "email codes from counting as two-factor authentication."
        ),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        from ninefruits.security.models import Role

        self.fields["mfa_enforcement"].choices = MfaEnforcement.choices()  # type: ignore[attr-defined]
        self.fields["mfa_required_role_ids"].choices = [  # type: ignore[attr-defined]
            (role.pk, role.display_label) for role in Role.objects.assignable()
        ]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if cleaned.get("mfa_enforcement") == MfaEnforcement.REQUIRED_FOR_ROLES and not cleaned.get(
            "mfa_required_role_ids"
        ):
            self.add_error("mfa_required_role_ids", _("Choose at least one role."))
        return cleaned


@register_settings_page
class ManageSecuritySettings(SettingsPage):
    settings_class = SecuritySettings
    permission = Permission.SECURITY_SETTINGS_MANAGE
    slug = "security"
    title = _("Security")
    icon = "shield"
    order = 10
    form_class = SecuritySettingsForm
    sections = (
        Section(
            _("Two-factor authentication"),
            [
                "mfa_enforcement",
                "mfa_required_role_ids",
                "mfa_grace_period_days",
                "mfa_remember_device_days",
                "mfa_email_code_enabled",
            ],
            description=_("Changes apply to every user immediately."),
        ),
    )

    def settings_data_from_form(self, cleaned_data: dict[str, Any]) -> dict[str, Any]:
        enforcement = MfaEnforcement(cleaned_data["mfa_enforcement"])
        return {
            "mfa_enforcement": enforcement,
            "mfa_required_role_ids": (
                [int(role_id) for role_id in cleaned_data.get("mfa_required_role_ids") or []]
                if enforcement == MfaEnforcement.REQUIRED_FOR_ROLES
                else []
            ),
            "mfa_grace_period_days": int(cleaned_data["mfa_grace_period_days"]),
            "mfa_remember_device_days": int(cleaned_data["mfa_remember_device_days"]),
            "mfa_email_code_enabled": bool(cleaned_data.get("mfa_email_code_enabled")),
        }


# -- authentication ------------------------------------------------------------------------------
class SsoProvidersWidget(forms.Widget):
    """A table of providers (original Filament ``Repeater``): one row per stored provider and
    one empty row to add a provider. Inputs are named ``<name>-<row>-<field>``."""

    template_name = "security/widgets/sso_providers.html"
    extra_rows = 1

    def format_value(self, value: Any) -> list[dict[str, Any]]:  # type: ignore[override]
        return list(value or [])

    def get_context(self, name: str, value: Any, attrs: dict[str, Any] | None) -> dict[str, Any]:
        context = super().get_context(name, value, attrs)
        rows = [{**row, "client_secret": ""} for row in self.format_value(value)]
        rows += [{"key": "", "scopes": DEFAULT_SCOPES, "is_enabled": True} for _ in range(self.extra_rows)]
        context["widget"]["rows"] = [
            {"index": index, "values": row, "prefix": f"{name}-{index}"} for index, row in enumerate(rows)
        ]
        # ninefruits.security.sso_urls: /auth/sso/<key>/callback/
        context["widget"]["redirect_uri"] = f"{django_settings.APP_URL.rstrip('/')}/auth/sso/{{key}}/callback/"
        return context

    def value_from_datadict(self, data: Any, files: Any, name: str) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        index = 0
        while f"{name}-{index}-key" in data:
            prefix = f"{name}-{index}-"
            if not data.get(prefix + "delete"):
                row: dict[str, Any] = {
                    field: str(data.get(prefix + field, "")).strip()
                    for field in PROVIDER_FIELDS
                    if field not in ("trusts_mfa", "is_enabled")
                }
                row["trusts_mfa"] = bool(data.get(prefix + "trusts_mfa"))
                row["is_enabled"] = bool(data.get(prefix + "is_enabled"))
                if any(row[field] for field in ("key", "label", "issuer", "client_id", "client_secret")):
                    rows.append(row)
            index += 1
        return rows

    def value_omitted_from_data(self, data: Any, files: Any, name: str) -> bool:
        return f"{name}-0-key" not in data


class SsoProvidersField(forms.Field):
    widget = SsoProvidersWidget

    def to_python(self, value: Any) -> list[dict[str, Any]]:
        return list(value or [])

    def validate(self, value: list[dict[str, Any]]) -> None:
        errors: list[str] = []
        seen: set[str] = set()
        url = URLValidator(schemes=["https", "http"])
        for row in value:
            key = row.get("key", "")
            name = key or "?"
            if not _KEY.match(key) or len(key) > 32:
                errors.append(str(_("%(key)s: the key uses lowercase letters, digits and hyphens.") % {"key": name}))
            if key in seen:
                errors.append(str(_("%(key)s: each provider needs its own key.") % {"key": name}))
            seen.add(key)
            if not row.get("label") or len(row["label"]) > 64:
                errors.append(str(_("%(key)s: the button label is required (64 characters at most).") % {"key": name}))
            try:
                url(row.get("issuer", ""))
            except ValidationError:
                errors.append(str(_("%(key)s: the issuer must be a URL.") % {"key": name}))
            if not row.get("client_id"):
                errors.append(str(_("%(key)s: the client ID is required.") % {"key": name}))
        if errors:
            raise ValidationError(errors)


class AuthenticationSettingsForm(forms.Form):
    student_number_login = forms.ChoiceField(label=_("Sign in with student number"), widget=UnfoldAdminSelectWidget)
    password_login_for_sso_users = forms.BooleanField(
        label=_("Allow passwords for users with school sign-in"),
        required=False,
        widget=UnfoldBooleanSwitchWidget,
        help_text=_("When off, users who have linked a school account must use it to sign in."),
    )
    lockout_threshold = _integer(
        _("Lock after failed attempts"),
        0,
        100,
        _("Failed passwords in a row before the account is locked. 0 turns locking off."),
    )
    lockout_minutes = _integer(_("Lock duration (minutes)"), 1, 1440)
    sso_link_mode = forms.ChoiceField(label=_("Account linking"), widget=UnfoldAdminSelectWidget)
    sso_providers = SsoProvidersField(label=_("Providers"), required=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["student_number_login"].choices = StudentNumberLogin.choices()  # type: ignore[attr-defined]
        self.fields["sso_link_mode"].choices = SsoLinkMode.choices()  # type: ignore[attr-defined]


@register_settings_page
class ManageAuthenticationSettings(SettingsPage):
    settings_class = AuthenticationSettings
    permission = Permission.AUTHENTICATION_SETTINGS_MANAGE
    slug = "authentication"
    title = _("Sign-in methods")
    icon = "key"
    order = 15
    form_class = AuthenticationSettingsForm
    sections = (
        Section(
            _("Passwords"),
            ["student_number_login", "password_login_for_sso_users", "lockout_threshold", "lockout_minutes"],
        ),
        Section(_("School sign-in (SSO)"), ["sso_link_mode", "sso_providers"]),
    )

    def initial_from_settings(self, settings: SettingsGroup) -> dict[str, Any]:
        initial = super().initial_from_settings(settings)
        initial["sso_providers"] = [{**provider, "client_secret": ""} for provider in initial["sso_providers"]]
        return initial

    def settings_data_from_form(self, cleaned_data: dict[str, Any]) -> dict[str, Any]:
        current = AuthenticationSettings.load()
        stored = {provider.get("key"): provider.get("client_secret") for provider in current.sso_providers}
        return {
            "student_number_login": StudentNumberLogin(cleaned_data["student_number_login"]),
            "password_login_for_sso_users": bool(cleaned_data.get("password_login_for_sso_users")),
            "sso_link_mode": SsoLinkMode(cleaned_data["sso_link_mode"]),
            "lockout_threshold": int(cleaned_data["lockout_threshold"]),
            "lockout_minutes": int(cleaned_data["lockout_minutes"]),
            "sso_providers": [
                {
                    "key": provider["key"],
                    "label": provider["label"],
                    "issuer": provider["issuer"].rstrip("/"),
                    "client_id": provider["client_id"],
                    "client_secret": (
                        encrypt_string(provider["client_secret"])
                        if provider.get("client_secret")
                        else stored.get(provider["key"])
                    ),
                    "scopes": provider.get("scopes") or DEFAULT_SCOPES,
                    "trusts_mfa": bool(provider.get("trusts_mfa")),
                    "is_enabled": bool(provider.get("is_enabled", True)),
                }
                for provider in cleaned_data.get("sso_providers") or []
            ],
        }
