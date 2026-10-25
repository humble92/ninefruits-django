"""Graduation policies (original ``App\\Policies\\Graduation\\DegreeAuditPolicy``, used for audits
and waivers). Registered from ``GraduationConfig.ready``. Stored audits and waivers are written by
the actions only; graduation staff and the student they belong to see them."""

from __future__ import annotations

from typing import Any

from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class DegreeAuditPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.GRADUATION_AUDIT) or user.has_perm(Permission.GRADUATION_PROCESS))

    def view(self, user: Any, obj: Any) -> bool:
        if self.view_any(user, obj):
            return True
        if obj is None or getattr(user, "person_id", None) is None:
            return False
        from ninefruits.person.models import StudentRecord

        return StudentRecord.objects.filter(pk=obj.student_record_id, person_id=user.person_id).exists()

    def create(self, user: Any, obj: Any) -> bool:
        return False

    def update(self, user: Any, obj: Any) -> bool:
        return False

    def delete(self, user: Any, obj: Any) -> bool:
        return False


def register_policies() -> None:
    policy = DegreeAuditPolicy()
    for label in ("graduation.degreeaudit", "graduation.degreerequirementwaiver"):
        register(label, policy)
