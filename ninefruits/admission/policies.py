"""Admission policies (original ``App\\Policies\\Admission\\*``). Registered from
``AdmissionConfig.ready``."""

from __future__ import annotations

from typing import Any

from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class AdmissionCyclePolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(
            user.has_perm(Permission.ADMISSION_CYCLES_MANAGE)
            or user.has_perm(Permission.APPLICATIONS_VIEW)
            or user.has_perm(Permission.APPLICATIONS_REVIEW)
        )

    def view(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)

    def create(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.ADMISSION_CYCLES_MANAGE))

    def update(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.ADMISSION_CYCLES_MANAGE))

    def delete(self, user: Any, obj: Any) -> bool:
        """Only cycles without applications (the database refuses others)."""
        return bool(user.has_perm(Permission.ADMISSION_CYCLES_MANAGE))


class ApplicationPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.APPLICATIONS_VIEW) or user.has_perm(Permission.APPLICATIONS_REVIEW))

    def view(self, user: Any, obj: Any) -> bool:
        return obj is not None and obj.is_visible_to(user)

    def create(self, user: Any, obj: Any) -> bool:
        """Applications are created by applicants in the portal."""
        return False

    def review(self, user: Any, obj: Any) -> bool:
        return obj is not None and obj.is_in_scope_of(user, Permission.APPLICATIONS_REVIEW)

    def matriculate(self, user: Any, obj: Any) -> bool:
        return obj is not None and obj.is_in_scope_of(user, Permission.APPLICATIONS_MATRICULATE)

    def update(self, user: Any, obj: Any) -> bool:
        return False

    def delete(self, user: Any, obj: Any) -> bool:
        return False


def register_admission_policies() -> None:
    register("admission.admissioncycle", AdmissionCyclePolicy())
    register("admission.application", ApplicationPolicy())
