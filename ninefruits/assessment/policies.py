"""Examination policies (original ``App\\Policies\\Assessment\\*``). Registered from
``AssessmentConfig.ready``.

- Kinds, areas and sessions (``AssessmentSetupPolicy``): reference data managed with
  ``assessments.manage``.
- Registrations, results and corrections (``AssessmentRecordPolicy``): written through the
  actions only; seen by staff who record or manage and by the student they belong to."""

from __future__ import annotations

from typing import Any

from ninefruits.institution.policies import ReferenceDataPolicy
from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class AssessmentRecordPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.ASSESSMENTS_RECORD) or user.has_perm(Permission.ASSESSMENTS_MANAGE))

    def view(self, user: Any, obj: Any) -> bool:
        if self.view_any(user, obj):
            return True
        if obj is None or getattr(user, "person_id", None) is None:
            return False
        from ninefruits.assessment.models import AssessmentResultCorrection
        from ninefruits.person.models import StudentRecord

        record_id = (
            obj.result.student_record_id if isinstance(obj, AssessmentResultCorrection) else obj.student_record_id
        )
        return StudentRecord.objects.filter(pk=record_id, person_id=user.person_id).exists()

    def create(self, user: Any, obj: Any) -> bool:
        return False

    def update(self, user: Any, obj: Any) -> bool:
        return False

    def delete(self, user: Any, obj: Any) -> bool:
        return False


def register_policies() -> None:
    setup = ReferenceDataPolicy(Permission.ASSESSMENTS_MANAGE)
    for label in ("assessment.assessmenttype", "assessment.assessmentcomponent", "assessment.assessmentsession"):
        register(label, setup)
    records = AssessmentRecordPolicy()
    for label in (
        "assessment.assessmentregistration",
        "assessment.assessmentresult",
        "assessment.assessmentcomponentscore",
        "assessment.assessmentresultcorrection",
    ):
        register(label, records)
