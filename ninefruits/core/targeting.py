"""Who something applies to (original ``App\\Support\\Targeting\\TargetCriteria`` and
``TargetSubject``, porting-plan 10.6, ADR 0006).

Criteria: programs, org units, admission year range, year levels, student statuses, academic
standings and tags. An empty criterion does not restrict; all non-empty criteria must match.
Term windows use them now; section eligibility, seat groups and registration rules later.

Stored as jsonb with only the non-empty criteria (``{}`` is everyone) through
:class:`TargetCriteriaField`::

    eligibility = TargetCriteriaField(null=True, blank=True)
    window.eligibility                    # TargetCriteria (everyone when NULL)
    window.eligibility = {"year_levels": [4]}
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from django.db import models
from django.db.models.query_utils import DeferredAttribute


@runtime_checkable
class TargetSubject(Protocol):
    """Something target criteria are checked against, usually a student record (Phase 2).
    Implementations return org units including all ancestors, so a criterion on a college
    matches a student of any of its departments."""

    def target_program_ids(self) -> list[int]: ...

    def target_org_unit_ids(self) -> list[int]:
        """Org units of the subject and all their ancestors."""
        ...

    def target_admission_year(self) -> int | None: ...

    def target_year_level(self) -> int | None: ...

    def target_student_status(self) -> str | None: ...

    def target_academic_standing(self) -> str | None: ...

    def target_tags(self) -> list[str]: ...


def _ints(values: Any) -> list[int]:
    if values is None:
        return []
    if isinstance(values, str | int):
        values = [values]
    return [int(value) for value in values]


def _strings(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    return [str(value) for value in values]


def _optional_int(value: Any) -> int | None:
    return None if value is None or value == "" else int(value)


@dataclass(frozen=True)
class TargetCriteria:
    program_ids: list[int] = field(default_factory=list)
    org_unit_ids: list[int] = field(default_factory=list)
    admission_year_from: int | None = None
    admission_year_to: int | None = None
    year_levels: list[int] = field(default_factory=list)
    student_statuses: list[str] = field(default_factory=list)
    academic_standings: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if (
            self.admission_year_from is not None
            and self.admission_year_to is not None
            and self.admission_year_from > self.admission_year_to
        ):
            raise ValueError("admission_year_from must not be after admission_year_to.")

    @classmethod
    def everyone(cls) -> TargetCriteria:
        return cls()

    def is_everyone(self) -> bool:
        return self.to_dict() == {}

    def matches(self, subject: TargetSubject) -> bool:
        if self.program_ids and not set(self.program_ids) & set(subject.target_program_ids()):
            return False
        if self.org_unit_ids and not set(self.org_unit_ids) & set(subject.target_org_unit_ids()):
            return False
        admission_year = subject.target_admission_year()
        if (self.admission_year_from is not None or self.admission_year_to is not None) and admission_year is None:
            return False
        if (
            self.admission_year_from is not None
            and admission_year is not None
            and admission_year < self.admission_year_from
        ):
            return False
        if (
            self.admission_year_to is not None
            and admission_year is not None
            and admission_year > self.admission_year_to
        ):
            return False
        if self.year_levels and subject.target_year_level() not in self.year_levels:
            return False
        if self.student_statuses and subject.target_student_status() not in self.student_statuses:
            return False
        if self.academic_standings and subject.target_academic_standing() not in self.academic_standings:
            return False
        return not self.tags or bool(set(self.tags) & set(subject.target_tags()))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None) -> TargetCriteria:
        data = data or {}
        return cls(
            program_ids=_ints(data.get("program_ids")),
            org_unit_ids=_ints(data.get("org_unit_ids")),
            admission_year_from=_optional_int(data.get("admission_year_from")),
            admission_year_to=_optional_int(data.get("admission_year_to")),
            year_levels=_ints(data.get("year_levels")),
            student_statuses=_strings(data.get("student_statuses")),
            academic_standings=_strings(data.get("academic_standings")),
            tags=_strings(data.get("tags")),
        )

    @classmethod
    def coerce(cls, value: Any) -> TargetCriteria:
        if isinstance(value, TargetCriteria):
            return value
        if value is None or value == "":
            return cls()
        if isinstance(value, Mapping):
            return cls.from_dict(value)
        raise TypeError(f"Target criteria are a dict or TargetCriteria, not {type(value).__name__}.")

    def to_dict(self) -> dict[str, Any]:
        """Only non-empty criteria, so "everyone" is stored as ``{}``. Key order is the
        original's."""
        values: dict[str, Any] = {
            "program_ids": list(self.program_ids),
            "org_unit_ids": list(self.org_unit_ids),
            "admission_year_from": self.admission_year_from,
            "admission_year_to": self.admission_year_to,
            "year_levels": list(self.year_levels),
            "student_statuses": list(self.student_statuses),
            "academic_standings": list(self.academic_standings),
            "tags": list(self.tags),
        }
        return {key: value for key, value in values.items() if value is not None and value != []}


class TargetCriteriaAttribute(DeferredAttribute):
    """Descriptor: reading gives a :class:`TargetCriteria` (everyone when NULL)."""

    def __get__(self, instance: models.Model | None, cls: type | None = None) -> Any:
        if instance is None:
            return self
        value = super().__get__(instance, cls)
        if not isinstance(value, TargetCriteria):
            value = TargetCriteria.coerce(value)
            instance.__dict__[self.field.attname] = value
        return value

    def __set__(self, instance: models.Model, value: Any) -> None:
        # A data descriptor, so assigned dicts (and NULL) read back as TargetCriteria too.
        instance.__dict__[self.field.attname] = TargetCriteria.coerce(value)


class TargetCriteriaField(models.JSONField):
    """jsonb column holding a :class:`TargetCriteria` (original ``TargetCriteria`` cast). A saved
    value is always an object, ``{}`` for everyone. Admin forms use
    ``ninefruits.core.forms.TargetCriteriaFormField``."""

    descriptor_class = TargetCriteriaAttribute
    description = "Target criteria (JSON object)"

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        return TargetCriteria.coerce(super().from_db_value(value, expression, connection))

    def to_python(self, value: Any) -> Any:
        if isinstance(value, TargetCriteria):
            return value
        return TargetCriteria.coerce(super().to_python(value))

    def get_prep_value(self, value: Any) -> Any:
        return super().get_prep_value(TargetCriteria.coerce(value).to_dict())

    def validate(self, value: Any, model_instance: models.Model | None) -> None:
        super().validate(TargetCriteria.coerce(value).to_dict(), model_instance)

    def value_to_string(self, obj: models.Model) -> str:
        return json.dumps(TargetCriteria.coerce(self.value_from_object(obj)).to_dict())
