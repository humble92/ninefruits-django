"""A person changes their own contact details in the portal (original
``UpdateOwnContactDetails``). Only ``Person.SELF_EDITABLE`` fields; everything else is changed by
staff (and audited by the data trigger either way)."""

from __future__ import annotations

from typing import Any

from django import forms
from django.core.exceptions import ValidationError

from ninefruits.person.models import Person


class _ContactForm(forms.Form):
    email = forms.EmailField(required=False, max_length=255)
    phone = forms.CharField(required=False, max_length=32)
    address = forms.CharField(required=False, max_length=1000)
    postal_code = forms.CharField(required=False, max_length=16)


class UpdateOwnContactDetails:
    def handle(self, user: Any, data: dict[str, Any]) -> Person:
        person = Person.objects.get(pk=user.person_id)
        submitted = {key: value for key, value in data.items() if key in Person.SELF_EDITABLE}
        form = _ContactForm(data=submitted)
        if not form.is_valid():
            raise ValidationError(form.errors.as_data())
        for field in submitted:
            setattr(person, field, form.cleaned_data[field] or None)
        person.save(update_fields=[*submitted, "updated_at"])
        return person

    __call__ = handle
