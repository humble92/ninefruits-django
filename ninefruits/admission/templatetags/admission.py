"""Template tags of the admission app (``{% load admission %}``)."""

from __future__ import annotations

from django import template

from ninefruits.admission.actions.registration import registration_enabled

register = template.Library()


@register.simple_tag
def applicant_registration_enabled() -> bool:
    """Whether applicants may create an account (sign-in page link to the admissions page)."""
    return registration_enabled()
