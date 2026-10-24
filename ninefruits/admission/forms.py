"""Forms of the admission screens: applicant sign-up (allauth ``ACCOUNT_FORMS["signup"]``,
original Fortify registration view) and the portal application forms."""

from __future__ import annotations

from typing import Any

from allauth.account.forms import SignupForm
from allauth.account.models import EmailAddress
from allauth.account.utils import setup_user_email
from django import forms
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from ninefruits.admission.actions import RegisterApplicant
from ninefruits.admission.actions.registration import registration_enabled


class ApplicantSignupForm(SignupForm):
    """Name (romanized), personal email and password. Saving creates the person and the account
    with ``RegisterApplicant``; allauth then mails the link to verify the address."""

    field_order = ["family_name", "given_name", "email", "password1", "password2"]

    family_name = forms.CharField(label=_("Family name"), max_length=255)
    given_name = forms.CharField(label=_("Given name"), max_length=255, required=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["email"].help_text = _("Your personal email. It stays your sign-in name after you graduate.")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        if not registration_enabled():
            self.add_error("email", _("Creating an account is not available. Contact the admissions office."))
        return cleaned

    def save(self, request: HttpRequest) -> Any:
        user = RegisterApplicant().handle(
            {
                "family_name": self.cleaned_data["family_name"],
                "given_name": self.cleaned_data.get("given_name") or "",
                "email": self.cleaned_data["email"],
                "password": self.cleaned_data["password1"],
            }
        )
        setup_user_email(request, user, [EmailAddress(email=user.email)])
        return user
