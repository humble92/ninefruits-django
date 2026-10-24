from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.grading.models import GradeScale


class SaveGradeScale:
    """Creates or updates a grade scale. The default scale is the institution's scale, fixed at
    installation (decided 2026-10-23): it can be set only while there is none, and never
    cleared or moved, because grades and GPAs already given are on it."""

    def __call__(self, scale: GradeScale | None, attributes: dict[str, Any]) -> GradeScale:
        with transaction.atomic():
            scale = scale or GradeScale()
            exists = scale.pk is not None
            wants_default = bool(attributes.get("is_default"))
            others = GradeScale.objects.filter(is_default=True)
            if exists:
                others = others.exclude(pk=scale.pk)
                stored_default = GradeScale.objects.filter(pk=scale.pk, is_default=True).exists()
            else:
                stored_default = False
            message = _("The grade scale is fixed at installation and cannot change.")
            if wants_default and others.exists():
                raise ValidationError({"is_default": message})
            if exists and stored_default and "is_default" in attributes and not wants_default:
                raise ValidationError({"is_default": message})
            for name, value in attributes.items():
                setattr(scale, name, value)
            scale.save()
            return scale
