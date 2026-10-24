"""Applicant self registration (original ``RegisterApplicant``, Fortify ``CreatesNewUsers``)."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import translation
from django.utils.translation import gettext as _

from ninefruits.admission.settings import AdmissionSettings
from ninefruits.audit.logger import audit
from ninefruits.core.db import session_context
from ninefruits.person.models import Person
from ninefruits.security.models import User


class _RegistrationForm(forms.Form):
    family_name = forms.CharField(max_length=255)
    given_name = forms.CharField(max_length=255, required=False)
    email = forms.EmailField(max_length=255)
    password = forms.CharField(strip=False)


class RegisterApplicant:
    """A person and an account with the personal email, which must be verified before applying.
    The account is kept for life (applicant, student, graduate). Runs as a system actor because
    the visitor has no account yet and row level security would not let them create a person
    (ADR 0008). The sign-up form (``ninefruits.admission.forms.ApplicantSignupForm``) calls this;
    allauth then records and mails the address to verify."""

    def handle(self, data: dict[str, Any]) -> User:
        if not registration_enabled():
            raise ValidationError({"email": _("Creating an account is not available. Contact the admissions office.")})

        form = _RegistrationForm(data=data)
        if not form.is_valid():
            raise ValidationError(form.errors.as_data())
        cleaned = form.cleaned_data
        email = str(cleaned["email"]).strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError({"email": _("The email has already been taken.")})
        validate_password(cleaned["password"], User(email=email))

        with session_context().system("registration"), transaction.atomic():
            person = Person.objects.create(
                family_name=cleaned["family_name"].strip(),
                given_name=(cleaned.get("given_name") or "").strip() or None,
                email=email,
            )
            user = User(person=person, name=None, email=email, locale=translation.get_language())
            user.set_password(cleaned["password"])
            user.save()
            audit("account.registered", user, properties={"person_id": person.pk}, causer=user, log="security")
        return user

    __call__ = handle


def registration_enabled() -> bool:
    return bool(AdmissionSettings.load().applicant_registration_enabled)
