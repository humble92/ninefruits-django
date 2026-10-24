"""Personas a user currently has (original ``PersonaResolver`` and ``PersonaDetector``).

Personas (applicant, student, alumni, instructor, advisor) are decided from domain data, never
assigned by hand. Each domain app registers its detector when its models exist (Phase 2:
student, alumni, instructor, advisor; Phase 3: applicant)::

    from ninefruits.security.services.personas import register_detector

    @register_detector
    class StudentDetector:
        persona = Persona.STUDENT
        def applies_to(self, user): ...

Until then no detector is registered and every persona check answers False. The resolver is
scoped like ``AuthorizationService`` (one per request or task)."""

from __future__ import annotations

import contextvars
from collections.abc import Iterable
from typing import TYPE_CHECKING, Protocol

from ninefruits.security.enums import Persona

if TYPE_CHECKING:
    from ninefruits.security.models import User


class PersonaDetector(Protocol):
    persona: Persona

    def applies_to(self, user: User) -> bool: ...


_detectors: list[PersonaDetector] = []


def register_detector[D: type](detector_class: D) -> D:
    """Class decorator: registers an instance of the detector."""
    instance = detector_class()
    if not any(type(existing) is detector_class for existing in _detectors):
        _detectors.append(instance)
    return detector_class


def registered_detectors() -> list[PersonaDetector]:
    return list(_detectors)


class PersonaResolver:
    def __init__(self, detectors: Iterable[PersonaDetector]) -> None:
        self.detectors = list(detectors)
        self._resolved: dict[int, list[Persona]] = {}

    def personas_for(self, user: User) -> list[Persona]:
        if user.pk in self._resolved:
            return self._resolved[user.pk]
        personas: list[Persona] = []
        for detector in self.detectors:
            if detector.applies_to(user) and detector.persona not in personas:
                personas.append(detector.persona)
        self._resolved[user.pk] = personas
        return personas

    def has(self, user: User, persona: Persona) -> bool:
        return persona in self.personas_for(user)

    def flush(self) -> None:
        self._resolved = {}


_current: contextvars.ContextVar[PersonaResolver | None] = contextvars.ContextVar(
    "ninefruits_persona_resolver", default=None
)


def persona_resolver() -> PersonaResolver:
    resolver = _current.get()
    if resolver is None:
        resolver = PersonaResolver(_detectors)
        _current.set(resolver)
    return resolver


def use_resolver(resolver: PersonaResolver | None) -> None:
    """Replaces the scoped resolver (tests use it to plug in their own detectors)."""
    _current.set(resolver)
    from . import authorization

    authorization._current.set(None)


def begin_scope() -> None:
    _current.set(None)
