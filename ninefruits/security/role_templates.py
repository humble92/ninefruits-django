"""Default roles based on the legacy Oracle roles (original
``database/seeders/Essential/RoleTemplateSeeder``, porting-plan 7.2, ADR 0005).

``sync_role_templates()`` is safe to run repeatedly: existing roles keep the display names and
permissions administrators gave them; system roles always get every permission, and persona
roles keep their persona link. The essential seeders of Phase 1 (``setup_install``) call it."""

from __future__ import annotations

from typing import TypedDict

from django.db import transaction

from ninefruits.security.actions import SyncPermissionCatalog
from ninefruits.security.enums import Permission as P
from ninefruits.security.enums import Persona
from ninefruits.security.models import GUARD_NAME, Role


class RoleTemplate(TypedDict, total=False):
    display_name: dict[str, str]
    is_system: bool
    permissions: list[P]


STAFF: list[P] = [P.ADMIN_PANEL_ACCESS, P.USERS_VIEW, P.REFERENCE_DATA_VIEW]

TEMPLATES: dict[str, RoleTemplate] = {
    "system_administrator": {
        "display_name": {
            "en": "System Administrator",
            "ko": "시스템 관리자",
            "zh-hans": "系统管理员",
            "lo": "ຜູ້ບໍລິຫານລະບົບ",
        },
        "is_system": True,
        "permissions": list(P),
    },
    "registrar": {
        "display_name": {"en": "Registrar", "ko": "학적 담당", "zh-hans": "学籍管理员", "lo": "ຜູ້ຮັບຜິດຊອບທະບຽນນັກສຶກສາ"},
        "permissions": [
            *STAFF,
            P.PEOPLE_VIEW,
            P.PEOPLE_MANAGE,
            P.PEOPLE_VIEW_SENSITIVE,
            P.PEOPLE_MERGE,
            P.ACCOUNTS_INVITE,
            P.STUDENT_RECORDS_VIEW,
            P.STUDENT_RECORDS_MANAGE,
            P.STUDENT_STATUS_CHANGES_APPROVE,
            P.ADVISORS_MANAGE,
            P.REFERENCE_DATA_IMPORT,
            P.APPLICATIONS_VIEW,
            P.APPLICATIONS_MATRICULATE,
            P.SECTIONS_VIEW,
            P.ADDITIONAL_PROGRAMS_APPROVE,
            P.ENROLLMENTS_VIEW,
            P.REGISTRATION_MANAGE,
            P.REGISTRATION_HOLDS_MANAGE,
            P.REGISTRATION_RULES_MANAGE,
            P.GRADES_VIEW,
            P.GRADES_MANAGE,
            P.GRADE_CHANGES_APPROVE,
            P.GRADE_EXCEPTIONS_REVIEW,
            P.CERTIFICATES_ISSUE,
            P.CERTIFICATES_MANAGE,
            P.ASSESSMENTS_RECORD,
            P.ASSESSMENTS_MANAGE,
            P.GRADUATION_AUDIT,
            P.GRADUATION_PROCESS,
            P.REPORTS_VIEW,
        ],
    },
    "academic_affairs": {
        "display_name": {"en": "Academic Affairs", "ko": "교무 담당", "zh-hans": "教务管理员", "lo": "ຜູ້ຮັບຜິດຊອບວິຊາການ"},
        "permissions": [
            *STAFF,
            P.REFERENCE_DATA_IMPORT,
            P.LOOKUP_VALUES_MANAGE,
            P.ORG_UNITS_MANAGE,
            P.PROGRAMS_MANAGE,
            P.FACILITIES_MANAGE,
            P.TERMS_MANAGE,
            P.TERM_WINDOWS_MANAGE,
            P.COURSE_CATEGORIES_MANAGE,
            P.GRADE_SCALES_MANAGE,
            P.INSTRUCTORS_MANAGE,
            P.STUDENT_RECORDS_VIEW,
            P.COURSES_MANAGE,
            P.CURRICULUM_MANAGE,
            P.SECTIONS_VIEW,
            P.SECTIONS_MANAGE,
            P.ENROLLMENTS_VIEW,
            P.REGISTRATION_RULES_MANAGE,
            P.GRADES_VIEW,
            P.GRADE_CHANGES_REQUEST,
            P.GRADING_POLICIES_MANAGE,
            P.EVALUATIONS_VIEW,
            P.EVALUATIONS_MANAGE,
            P.CERTIFICATES_MANAGE,
            P.ASSESSMENTS_RECORD,
            P.ASSESSMENTS_MANAGE,
            P.GRADUATION_AUDIT,
            P.REPORTS_VIEW,
            P.LMS_MANAGE,
        ],
    },
    "certificate_officer": {
        "display_name": {
            "en": "Certificate Officer",
            "ko": "증명서 담당",
            "zh-hans": "证明书管理员",
            "lo": "ຜູ້ຮັບຜິດຊອບໃບຢັ້ງຢືນ",
        },
        "permissions": [*STAFF, P.STUDENT_RECORDS_VIEW, P.GRADES_VIEW, P.CERTIFICATES_ISSUE],
    },
    # Assign with an org unit scope: the assistant sees that unit's students.
    "department_assistant": {
        "display_name": {"en": "Department Assistant", "ko": "학과 조교", "zh-hans": "院系助理", "lo": "ຜູ້ຊ່ວຍພາກວິຊາ"},
        "permissions": [
            *STAFF,
            P.STUDENT_RECORDS_VIEW,
            P.REPORTS_VIEW,
            P.ADVISORS_MANAGE,
            P.APPLICATIONS_VIEW,
            P.SECTIONS_VIEW,
            P.SECTIONS_MANAGE,
            P.ADDITIONAL_PROGRAMS_APPROVE,
            P.ENROLLMENTS_VIEW,
            P.REGISTRATION_MANAGE,
            P.GRADES_VIEW,
            P.EVALUATIONS_VIEW,
        ],
    },
    "admissions_officer": {
        "display_name": {
            "en": "Admissions Officer",
            "ko": "입학 담당",
            "zh-hans": "招生管理员",
            "lo": "ຜູ້ຮັບຜິດຊອບການຮັບເຂົ້າຮຽນ",
        },
        "permissions": [
            *STAFF,
            P.ADMISSION_CYCLES_MANAGE,
            P.APPLICATIONS_VIEW,
            P.APPLICATIONS_REVIEW,
            P.APPLICATIONS_MATRICULATE,
        ],
    },
}

PERSONAS: dict[Persona, dict[str, str]] = {
    Persona.APPLICANT: {"en": "Applicant", "ko": "지원자", "zh-hans": "申请人", "lo": "ຜູ້ສະໝັກ"},
    Persona.STUDENT: {"en": "Student", "ko": "학생", "zh-hans": "学生", "lo": "ນັກສຶກສາ"},
    Persona.ALUMNI: {"en": "Alumni", "ko": "졸업생", "zh-hans": "校友", "lo": "ສິດເກົ່າ"},
    Persona.INSTRUCTOR: {"en": "Instructor", "ko": "교원", "zh-hans": "教师", "lo": "ອາຈານ"},
    Persona.ADVISOR: {"en": "Advisor", "ko": "지도교수", "zh-hans": "指导教师", "lo": "ອາຈານທີ່ປຶກສາ"},
}


@transaction.atomic
def sync_role_templates() -> list[str]:
    """Creates the missing template and persona roles. Returns the names of created roles."""
    SyncPermissionCatalog()()
    created: list[str] = []
    for name, template in TEMPLATES.items():
        role, was_created = Role.objects.get_or_create(
            name=name,
            guard_name=GUARD_NAME,
            defaults={"display_name": template["display_name"], "is_system": template.get("is_system", False)},
        )
        if was_created:
            created.append(name)
        if was_created or role.is_system:
            role.sync_permissions([permission.value for permission in template["permissions"]])

    for persona, display_name in PERSONAS.items():
        role, was_created = Role.objects.get_or_create(
            name=persona.value,
            guard_name=GUARD_NAME,
            defaults={"display_name": display_name, "persona": persona.value},
        )
        if was_created:
            created.append(persona.value)
        # The persona link is what grants the role; keep it even if someone cleared it.
        if role.persona != persona.value:
            role.persona = persona.value
            role.save(update_fields=["persona", "updated_at"])
    return created
