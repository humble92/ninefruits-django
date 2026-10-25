from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.offering.models import Section, Syllabus

TEXT_PARTS = ("overview", "objectives", "materials", "policies")


def _required(name: str) -> str:
    return _("The %(attribute)s field is required.") % {"attribute": name.replace("_", " ")}


def _validate(language: str, content: Mapping[str, Any]) -> dict[str, Any]:
    """The original's validation rules, keyed like Laravel (``weekly_plan.0.week``)."""
    errors: dict[str, str] = {}
    language = (language or "").strip()
    if not language:
        errors["language"] = _required("language")
    elif len(language) > 16:
        errors["language"] = _("The %(attribute)s field must not be greater than %(max)s characters.") % {
            "attribute": "language",
            "max": 16,
        }
    data: dict[str, Any] = {}
    for part in TEXT_PARTS:
        value = content.get(part)
        if value in (None, ""):
            data[part] = None
            continue
        if not isinstance(value, str):
            errors[part] = _("The %(attribute)s field must be a string.") % {"attribute": part}
        elif len(value) > 5000:
            errors[part] = _("The %(attribute)s field must not be greater than %(max)s characters.") % {
                "attribute": part,
                "max": 5000,
            }
        data[part] = value

    assessment = list(content.get("assessment") or [])
    if len(assessment) > 20:
        errors["assessment"] = _("The %(attribute)s field must not have more than %(max)s items.") % {
            "attribute": "assessment",
            "max": 20,
        }
    items = []
    for index, row in enumerate(assessment):
        item = str((row or {}).get("item") or "").strip()
        weight: Any = (row or {}).get("weight")
        if not item:
            errors[f"assessment.{index}.item"] = _required(f"assessment.{index}.item")
        elif len(item) > 255:
            errors[f"assessment.{index}.item"] = _(
                "The %(attribute)s field must not be greater than %(max)s characters."
            ) % {"attribute": f"assessment.{index}.item", "max": 255}
        if weight in ("", None):
            weight = None
        else:
            try:
                number = Decimal(str(weight))
            except InvalidOperation:
                number = None
            if number is None or not Decimal(0) <= number <= Decimal(100):
                errors[f"assessment.{index}.weight"] = _(
                    "The %(attribute)s field must be between %(min)s and %(max)s."
                ) % {"attribute": f"assessment.{index}.weight", "min": 0, "max": 100}
            else:
                weight = int(number) if number == number.to_integral_value() else float(number)
        items.append({"item": item, "weight": weight})

    weekly = list(content.get("weekly_plan") or [])
    if len(weekly) > 30:
        errors["weekly_plan"] = _("The %(attribute)s field must not have more than %(max)s items.") % {
            "attribute": "weekly_plan",
            "max": 30,
        }
    weeks = []
    for index, row in enumerate(weekly):
        topic = str((row or {}).get("topic") or "").strip()
        raw_week = (row or {}).get("week")
        try:
            week = int(str(raw_week))
        except TypeError, ValueError:
            week = None
            errors[f"weekly_plan.{index}.week"] = _("The %(attribute)s field must be an integer.") % {
                "attribute": f"weekly_plan.{index}.week"
            }
        if week is not None and not 1 <= week <= 30:
            errors[f"weekly_plan.{index}.week"] = _("The %(attribute)s field must be between %(min)s and %(max)s.") % {
                "attribute": f"weekly_plan.{index}.week",
                "min": 1,
                "max": 30,
            }
        if not topic:
            errors[f"weekly_plan.{index}.topic"] = _required(f"weekly_plan.{index}.topic")
        elif len(topic) > 500:
            errors[f"weekly_plan.{index}.topic"] = _(
                "The %(attribute)s field must not be greater than %(max)s characters."
            ) % {"attribute": f"weekly_plan.{index}.topic", "max": 500}
        weeks.append({"week": week, "topic": topic})

    if errors:
        raise ValidationError(errors)
    return {"language": language, **data, "assessment": items, "weekly_plan": weeks}


class UpdateSyllabus:
    """The section's instructors (or staff who manage the section) write the syllabus and
    publish it for students. Changes after publishing stay published."""

    def __call__(
        self,
        section: Section,
        language: str,
        content: Mapping[str, Any],
        user: Any,
        publish: bool | None = None,
    ) -> Syllabus:
        if not section.is_taught_by(user) and not section.is_manageable_by(user):
            raise PermissionDenied
        data = _validate(language, content)
        syllabus = Syllabus.objects.filter(section_id=section.pk).first() or Syllabus(section=section)
        syllabus.language = data.pop("language")
        syllabus.content = data
        syllabus.updated_by_id = user.pk
        if publish is not None:
            syllabus.published_at = (
                (syllabus.published_at or timezone.now().replace(microsecond=0)) if publish else None
            )
        syllabus.save()
        return syllabus
