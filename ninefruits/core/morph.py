"""Polymorphic references (``subject_type``/``subject_id``, ``model_type``/``model_id``).
The original stored PHP class names; Django stores the model label in lower case
(``person.person``). See ADR 0002-django."""

from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db import models


def morph_type(obj: models.Model | type[models.Model]) -> str:
    return obj._meta.label_lower


def morph_of(obj: models.Model | None) -> tuple[str | None, Any]:
    if obj is None:
        return None, None
    return morph_type(obj), obj.pk


def resolve(type_name: str | None, pk: Any) -> models.Model | None:
    if not type_name or pk is None:
        return None
    model = apps.get_model(type_name)
    return model._default_manager.filter(pk=pk).first()
