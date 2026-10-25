"""Outcomes of a degree audit (original ``App\\Domain\\Graduation\\Data``): one
``DegreeAuditResult`` per program of the student, one ``RequirementResult`` per requirement of
the set. ``to_dict()`` is the snapshot stored in ``degree_audits.result`` (same keys as the
original, so stored audits read the same in both applications)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


def as_number(value: Decimal | float | int | None) -> float | None:
    """A JSON number as the original stored it (PHP floats: ``12.0``)."""
    return None if value is None else float(value)


@dataclass(frozen=True)
class RequirementResult:
    """One requirement of the set against what the student achieved. ``courses`` are the
    enrollments counted (code, title, credits, grade), ``missing`` the codes of required courses
    not passed."""

    requirement_id: int
    kind: str
    name: str
    required_credits: Decimal | None
    required_courses: int | None
    achieved_credits: Decimal
    achieved_courses: int
    is_satisfied: bool
    is_waived: bool
    courses: list[dict[str, Any]] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "kind": str(self.kind),
            "name": self.name,
            "required_credits": as_number(self.required_credits),
            "required_courses": self.required_courses,
            "achieved_credits": as_number(self.achieved_credits),
            "achieved_courses": self.achieved_courses,
            "satisfied": self.is_satisfied,
            "waived": self.is_waived,
            "courses": self.courses,
            "missing": self.missing,
        }


@dataclass(frozen=True)
class DegreeAuditResult:
    """The outcome of a degree audit for one program of the student. ``issues`` say in words
    (already translated) why it is not satisfied."""

    program: Any
    role: str
    requirement_set: Any
    earned_credits: Decimal
    required_credits: Decimal | None
    cumulative_gpa: Decimal | None
    minimum_gpa: Decimal | None
    requirements: list[RequirementResult]
    issues: list[str]

    def is_satisfied(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_id": self.program.pk,
            "program_code": self.program.code,
            "role": str(self.role),
            "set_id": getattr(self.requirement_set, "pk", None),
            "earned_credits": as_number(self.earned_credits),
            "required_credits": as_number(self.required_credits),
            "cumulative_gpa": as_number(self.cumulative_gpa),
            "minimum_gpa": as_number(self.minimum_gpa),
            "satisfied": self.is_satisfied(),
            "issues": list(self.issues),
            "requirements": [requirement.to_dict() for requirement in self.requirements],
        }


def for_display(snapshot: dict[str, Any]) -> dict[str, Any]:
    """A snapshot (``to_dict()`` or a stored ``result``) with the translated role for the
    templates (original ``__('curriculum.program_roles.'.$result['role'])``)."""
    from ninefruits.curriculum.enums import ProgramRole

    role = snapshot.get("role")
    label = str(ProgramRole(role).label) if role in ProgramRole.values else str(role or "")
    return {**snapshot, "role_label": label}
