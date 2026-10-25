"""Whether a student has passed a kind (original ``AssessmentPassCheck``): any passing result,
from a session or external. Also the kinds the student's primary curriculum requires. The
graduation audit (Phase 11) calls this for ``assessment_pass`` requirements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ninefruits.assessment.models import AssessmentResult, AssessmentType


@dataclass(frozen=True, slots=True)
class RequiredAssessment:
    type: AssessmentType
    passed: bool


class AssessmentPassCheck:
    def has_passed(self, record: Any, kind: AssessmentType) -> bool:
        return AssessmentResult.objects.filter(
            student_record_id=record.pk, assessment_type_id=kind.pk, is_passed=True
        ).exists()

    def required(self, record: Any) -> list[RequiredAssessment]:
        """The kinds the student's primary curriculum requires, with the pass state."""
        from ninefruits.curriculum.enums import ProgramRole, RequirementKind
        from ninefruits.curriculum.models import CurriculumRequirement, CurriculumRequirementSet

        requirement_set = (
            CurriculumRequirementSet.objects.filter(program_id=record.program_id, program_role=ProgramRole.PRIMARY)
            .for_catalog_year(record.catalog_year)
            .first()
        )
        if requirement_set is None:
            return []
        passed_ids = set(
            AssessmentResult.objects.filter(student_record_id=record.pk, is_passed=True).values_list(
                "assessment_type_id", flat=True
            )
        )
        requirements = (
            CurriculumRequirement.objects.filter(
                requirement_set_id=requirement_set.pk, kind=RequirementKind.ASSESSMENT_PASS
            )
            .select_related("assessment_type")
            .order_by("sort_order", "id")
        )
        return [
            RequiredAssessment(type=requirement.assessment_type, passed=requirement.assessment_type_id in passed_ids)
            for requirement in requirements
            if requirement.assessment_type is not None
        ]
