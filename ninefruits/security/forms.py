"""Sign-in forms (allauth ``ACCOUNT_FORMS``)."""

from __future__ import annotations

from typing import Any

from allauth.account.adapter import get_adapter
from allauth.account.forms import LoginForm as AllauthLoginForm
from allauth.account.internal import flows
from allauth.account.models import Login
from allauth.core import context
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.audit.security_events import SecurityEventType, record_security_event


class LoginForm(AllauthLoginForm):  # type: ignore[misc]  # django-allauth has no type information
    """Email or student number (institution setting) and password. Every failure, including
    deactivated, locked and SSO-only accounts, gets the same message (original
    ``Fortify::authenticateUsing``)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        from ninefruits.security.services.login_identifier import LoginIdentifierResolver

        student_numbers = LoginIdentifierResolver().allows_student_numbers()
        self.fields["login"] = forms.CharField(
            label=_("Email or student number") if student_numbers else pgettext_lazy("authentication", "Email"),
            widget=forms.TextInput(
                attrs={
                    "type": "text" if student_numbers else "email",
                    "autocomplete": "username",
                    "autofocus": True,
                }
            ),
        )
        self.fields["password"].label = pgettext_lazy("authentication", "Password")
        if "remember" in self.fields:
            self.fields["remember"].label = _("Keep me signed in")
        self.order_fields(["login", "password", "remember"])

    def user_credentials(self) -> dict[str, Any]:
        login = self.cleaned_data["login"]
        credentials: dict[str, Any] = {"login": login, "email": login if "@" in login else None}
        password = self.cleaned_data.get("password")
        if password:
            credentials["password"] = password
        return {key: value for key, value in credentials.items() if value is not None}

    def _clean_with_password(self, credentials: dict[str, Any]) -> dict[str, Any]:
        adapter = get_adapter(self.request)
        try:
            user = adapter.authenticate(self.request, **credentials)
        except ValidationError:
            # Rate limited (allauth ``login_failed`` limit): original Lockout event.
            record_security_event(SecurityEventType.LOGIN_LOCKED_OUT, identifier=str(credentials.get("login"))[:255])
            raise
        if not user:
            raise adapter.validation_error("email_password_mismatch")
        login = Login(user=user, email=credentials.get("email"))
        if flows.login.is_login_rate_limited(context.request, login):
            raise adapter.validation_error("too_many_login_attempts")
        self._login = login
        self.user = user
        cleaned: dict[str, Any] = self.cleaned_data
        return cleaned
