"""Curriculum policies (original ``App\\Policies\\Curriculum\\CoursePolicy`` and
``CurriculumPolicy``): anyone with ``reference_data.view`` looks, the manage permission changes."""

from __future__ import annotations

from ninefruits.institution.policies import ReferenceDataPolicy
from ninefruits.security.enums import Permission
from ninefruits.security.policies import register

#: Courses, their versions, requisites and equivalencies; graduation requirement sets and lines.
CURRICULUM_POLICIES: dict[str, Permission] = {
    "curriculum.course": Permission.COURSES_MANAGE,
    "curriculum.courseversion": Permission.COURSES_MANAGE,
    "curriculum.courserequisite": Permission.COURSES_MANAGE,
    "curriculum.courseequivalency": Permission.COURSES_MANAGE,
    "curriculum.curriculumrequirementset": Permission.CURRICULUM_MANAGE,
    "curriculum.curriculumrequirement": Permission.CURRICULUM_MANAGE,
}


def register_policies() -> None:
    for label, permission in CURRICULUM_POLICIES.items():
        register(label, ReferenceDataPolicy(permission))
