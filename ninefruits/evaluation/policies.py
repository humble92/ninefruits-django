"""Course evaluation policies (original ``EvaluationSetupPolicy`` for forms, questions and term
evaluations: anyone with ``reference_data.view`` can look, ``evaluations.manage`` changes).
Responses and completions are never edited; the response screen needs ``evaluations.view`` or
``evaluations.manage`` (original ``SectionEvaluationResource::canViewAny``). Registered from
``EvaluationConfig.ready``."""

from __future__ import annotations

from typing import Any

from ninefruits.institution.policies import ReferenceDataPolicy
from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class SectionEvaluationPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.EVALUATIONS_VIEW) or user.has_perm(Permission.EVALUATIONS_MANAGE))

    def view(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)

    def create(self, user: Any, obj: Any) -> bool:
        return False

    def update(self, user: Any, obj: Any) -> bool:
        return False

    def delete(self, user: Any, obj: Any) -> bool:
        return False


def register_policies() -> None:
    setup = ReferenceDataPolicy(Permission.EVALUATIONS_MANAGE)
    for label in ("evaluation.evaluationform", "evaluation.evaluationquestion", "evaluation.termevaluation"):
        register(label, setup)
    register("evaluation.sectionevaluation", SectionEvaluationPolicy())
