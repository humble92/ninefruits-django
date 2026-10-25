"""Applicant persona (original ``App\\Domain\\Admission\\Personas\\ApplicantPersonaDetector``)
and the person visibility extension (original ``Person::constrainVisibleTo``
``orWhereHas('applications', ...)``)."""

from __future__ import annotations

from typing import Any

from django.db.models import Q

from ninefruits.admission.models import Application
from ninefruits.person.models import PERSON_VISIBILITY
from ninefruits.security.enums import Persona
from ninefruits.security.services.personas import register_detector


@register_detector
class ApplicantPersonaDetector:
    """Applicant: has an application that is still open and not yet matriculated. A student or
    graduate applying again is an applicant too."""

    persona = Persona.APPLICANT

    def applies_to(self, user: Any) -> bool:
        return (
            user.person_id is not None
            and Application.objects.filter(person_id=user.person_id, student_record__isnull=True).open().exists()
        )


def people_with_visible_applications(user: Any) -> Q:
    """People whose applications the user can see (staff by scope, and the applicant)."""
    return Q(pk__in=Application.objects.visible_to(user).values("person_id"))


if people_with_visible_applications not in PERSON_VISIBILITY:
    PERSON_VISIBILITY.append(people_with_visible_applications)
