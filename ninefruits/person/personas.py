"""Persona detectors (original ``App\\Domain\\Person\\Personas``). Applicants are detected by the
admission app (Phase 3) with the same ``register_detector`` hook."""

from __future__ import annotations

from typing import Any

from ninefruits.person.enums import StudentStatus
from ninefruits.person.models import AdvisorAssignment, Instructor, StudentRecord
from ninefruits.security.enums import Persona
from ninefruits.security.services.personas import register_detector


@register_detector
class StudentPersonaDetector:
    """Student: has a current (enrolled or on leave) student record."""

    persona = Persona.STUDENT

    def applies_to(self, user: Any) -> bool:
        return user.person_id is not None and StudentRecord.objects.filter(person_id=user.person_id).active().exists()


@register_detector
class AlumniPersonaDetector:
    """Alumni: has a graduated student record (also while studying again on a new record)."""

    persona = Persona.ALUMNI

    def applies_to(self, user: Any) -> bool:
        return (
            user.person_id is not None
            and StudentRecord.objects.filter(person_id=user.person_id, status=StudentStatus.GRADUATED).exists()
        )


@register_detector
class InstructorPersonaDetector:
    """Instructor: has a current instructor record."""

    persona = Persona.INSTRUCTOR

    def applies_to(self, user: Any) -> bool:
        return user.person_id is not None and Instructor.objects.filter(person_id=user.person_id).current().exists()


@register_detector
class AdvisorPersonaDetector:
    """Advisor: advises at least one student today."""

    persona = Persona.ADVISOR

    def applies_to(self, user: Any) -> bool:
        return (
            user.person_id is not None
            and AdvisorAssignment.objects.current().filter(instructor__person_id=user.person_id).exists()
        )
