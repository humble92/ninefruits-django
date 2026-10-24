"""Grading policies (original ``App\\Policies\\Grading\\*``). Requests are made from the grade entry
screen and decided through the actions; term records are calculated, never edited by hand.
Registered from ``GradingConfig.ready``."""

from __future__ import annotations

from typing import Any

from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class _ReadOnly(Policy):
    def create(self, user: Any, obj: Any) -> bool:
        return False

    def update(self, user: Any, obj: Any) -> bool:
        return False

    def delete(self, user: Any, obj: Any) -> bool:
        return False


class TermRecordPolicy(_ReadOnly):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.GRADES_VIEW) or user.has_perm(Permission.GRADES_MANAGE))

    def view(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)


class GradeChangeRequestPolicy(_ReadOnly):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(
            user.has_perm(Permission.GRADE_CHANGES_APPROVE)
            or user.has_perm(Permission.GRADE_CHANGES_REQUEST)
            or user.has_perm(Permission.GRADES_VIEW)
        )

    def view(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj) or (obj is not None and obj.requested_by_id == user.pk)


class EvaluationMethodRequestPolicy(_ReadOnly):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.SECTIONS_MANAGE) or user.has_perm(Permission.GRADES_VIEW))

    def view(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)


class SectionGradePolicy(_ReadOnly):
    """The grade progress screen (original ``SectionGradeResource::canViewAny``)."""

    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.GRADES_VIEW) or user.has_perm(Permission.GRADES_MANAGE))

    def view(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)


def register_policies() -> None:
    register("grading.termrecord", TermRecordPolicy())
    register("grading.gradechangerequest", GradeChangeRequestPolicy())
    register("grading.evaluationmethodrequest", EvaluationMethodRequestPolicy())
    register("grading.sectiongrade", SectionGradePolicy())
