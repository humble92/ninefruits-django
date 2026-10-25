"""Account creation from an invitation link: the person chooses a password (original
``InvitationController``)."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views import View
from django_ratelimit.decorators import ratelimit

from ninefruits.person.actions import AcceptInvitation

LOGIN_BACKEND = "ninefruits.security.backends.LoginIdentifierBackend"


class InvitationPasswordForm(forms.Form):
    password = forms.CharField(label=gettext_lazy("New password"), widget=forms.PasswordInput, strip=False)
    password_confirmation = forms.CharField(
        label=gettext_lazy("Confirm password"), widget=forms.PasswordInput, strip=False
    )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        password = cleaned.get("password")
        if password and password != cleaned.get("password_confirmation"):
            self.add_error("password", _("The password field confirmation does not match."))
        elif password:
            try:
                validate_password(password)
            except ValidationError as error:
                self.add_error("password", error)
        return cleaned


class InvitationView(View):
    template_name = "person/accept_invitation.html"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        if request.user.is_authenticated:
            return redirect("portal:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def _render(self, request: HttpRequest, token: str, form: forms.Form, status: int = 200) -> HttpResponse:
        invitation = AcceptInvitation.find(token)
        return render(
            request,
            self.template_name,
            {"token": token, "email": invitation.email if invitation else None, "form": form},
            status=status,
        )

    def get(self, request: HttpRequest, token: str) -> HttpResponse:
        return self._render(request, token, InvitationPasswordForm())

    @method_decorator(ratelimit(key="ip", rate="6/m", method="POST", block=True))
    def post(self, request: HttpRequest, token: str) -> HttpResponse:
        form = InvitationPasswordForm(request.POST)
        if not form.is_valid():
            return self._render(request, token, form, status=422)
        try:
            user = AcceptInvitation().handle(token, form.cleaned_data["password"])
        except ValidationError as error:
            for message in error.message_dict.get("token", []):
                form.add_error(None, message)
            return self._render(request, token, form, status=422)
        login(request, user, backend=LOGIN_BACKEND)
        messages.success(request, _("Your account is ready. Welcome."))
        return redirect("portal:dashboard")
