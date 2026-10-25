"""What the portal shows a user: personas and active roles (original ``PersonaResolver`` and
``AuthorizationService::activeRoleNames``, implemented in ``ninefruits.security.services``).

Personas are cached on the request because the layout, the menu and the dashboard all ask."""

from __future__ import annotations

from typing import Any

from django.http import HttpRequest

from ninefruits.security.services.authorization import authorization


def personas_for(request: HttpRequest) -> list[Any]:
    """The signed-in user's personas (``Persona`` members), cached on the request."""
    cached = getattr(request, "_portal_personas", None)
    if cached is None:
        user = request.user
        cached = list(authorization().personas.personas_for(user)) if user.is_authenticated else []
        request._portal_personas = cached  # type: ignore[attr-defined]
    return list(cached)


def persona_values(request: HttpRequest) -> set[str]:
    return {str(getattr(persona, "value", persona)) for persona in personas_for(request)}


def persona_label(persona: Any) -> str:
    return str(getattr(persona, "label", persona))


def active_role_names(request: HttpRequest) -> list[str]:
    """Roles the user holds today, for display."""
    user = request.user
    if not user.is_authenticated:
        return []
    return [str(name) for name in authorization().active_role_names(user)]
