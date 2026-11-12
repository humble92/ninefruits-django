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
            "de": "Systemadministration",
            "ru": "Системный администратор",
            "ms": "Pentadbir Sistem",
            "fil": "Administrator ng Sistema",
            "fr": "Administrateur système",
            "ja": "システム管理者",
            "mn": "Системийн админ",
            "ne": "प्रणाली प्रशासक",
            "th": "ผู้ดูแลระบบ",
            "tr": "Sistem Yöneticisi",
            "uz": "Tizim administratori",
            "vi": "Quản trị hệ thống",
        },
        "is_system": True,
        "permissions": list(P),
    },
    "registrar": {
        "display_name": {
            "en": "Registrar",
            "ko": "학적 담당",
            "zh-hans": "学籍管理员",
            "lo": "ຜູ້ຮັບຜິດຊອບທະບຽນນັກສຶກສາ",
            "de": "Studierendensekretariat",
            "ru": "Сотрудник учебного отдела",
            "ms": "Pegawai Pendaftar",
            "fil": "Registrar",
            "fr": "Scolarité",
            "ja": "学籍担当",
            "mn": "Оюутны бүртгэл хариуцсан ажилтан",
            "ne": "रजिस्ट्रार",
            "th": "เจ้าหน้าที่ทะเบียน",
            "tr": "Öğrenci İşleri",
            "uz": "Registrator",
            "vi": "Cán bộ quản lý sinh viên",
        },
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
        "display_name": {
            "en": "Academic Affairs",
            "ko": "교무 담당",
            "zh-hans": "教务管理员",
            "lo": "ຜູ້ຮັບຜິດຊອບວິຊາການ",
            "de": "Lehrplanung",
            "ru": "Сотрудник учебного управления",
            "ms": "Pegawai Hal Ehwal Akademik",
            "fil": "Academic Affairs",
            "fr": "Affaires pédagogiques",
            "ja": "教務担当",
            "mn": "Сургалтын албаны ажилтан",
            "ne": "शैक्षिक प्रशासन",
            "th": "เจ้าหน้าที่ฝ่ายวิชาการ",
            "tr": "Akademik İşler",
            "uz": "Oʻquv-uslubiy boshqarma",
            "vi": "Cán bộ đào tạo",
        },
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
            "de": "Bescheinigungsstelle",
            "ru": "Ответственный за справки",
            "ms": "Pegawai Sijil",
            "fil": "Tagapangasiwa ng Sertipiko",
            "fr": "Responsable des attestations",
            "ja": "証明書担当",
            "mn": "Тодорхойлолт хариуцсан ажилтан",
            "ne": "प्रमाणपत्र अधिकृत",
            "th": "เจ้าหน้าที่ออกหนังสือรับรอง",
            "tr": "Belge Sorumlusu",
            "uz": "Maʼlumotnomalar masʼuli",
            "vi": "Cán bộ cấp giấy chứng nhận",
        },
        "permissions": [*STAFF, P.STUDENT_RECORDS_VIEW, P.GRADES_VIEW, P.CERTIFICATES_ISSUE],
    },
    # Assign with an org unit scope: the assistant sees that unit's students.
    "department_assistant": {
        "display_name": {
            "en": "Department Assistant",
            "ko": "학과 조교",
            "zh-hans": "院系助理",
            "lo": "ຜູ້ຊ່ວຍພາກວິຊາ",
            "de": "Institutssekretariat",
            "ru": "Методист кафедры",
            "ms": "Pembantu Jabatan",
            "fil": "Katuwang ng Departamento",
            "fr": "Gestionnaire de département",
            "ja": "学科助手",
            "mn": "Тэнхимийн туслах ажилтан",
            "ne": "विभागीय सहायक",
            "th": "เจ้าหน้าที่ภาควิชา",
            "tr": "Bölüm Asistanı",
            "uz": "Kafedra yordamchisi",
            "vi": "Giáo vụ khoa",
        },
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
            "de": "Zulassungsstelle",
            "ru": "Сотрудник приёмной комиссии",
            "ms": "Pegawai Kemasukan",
            "fil": "Admissions Officer",
            "fr": "Chargé des admissions",
            "ja": "入試担当",
            "mn": "Элсэлт хариуцсан ажилтан",
            "ne": "भर्ना अधिकृत",
            "th": "เจ้าหน้าที่รับสมัคร",
            "tr": "Öğrenci Kabul Sorumlusu",
            "uz": "Qabul komissiyasi xodimi",
            "vi": "Cán bộ tuyển sinh",
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
    Persona.APPLICANT: {
        "en": "Applicant",
        "ko": "지원자",
        "zh-hans": "申请人",
        "lo": "ຜູ້ສະໝັກ",
        "de": "Bewerber/in",
        "ru": "Абитуриент",
        "ms": "Pemohon",
        "fil": "Aplikante",
        "fr": "Candidat",
        "ja": "志願者",
        "mn": "Өргөдөл гаргагч",
        "ne": "आवेदक",
        "th": "ผู้สมัคร",
        "tr": "Aday",
        "uz": "Abituriyent",
        "vi": "Thí sinh",
    },
    Persona.STUDENT: {
        "en": "Student",
        "ko": "학생",
        "zh-hans": "学生",
        "lo": "ນັກສຶກສາ",
        "de": "Studierende/r",
        "ru": "Студент",
        "ms": "Pelajar",
        "fil": "Mag-aaral",
        "fr": "Étudiant",
        "ja": "学生",
        "mn": "Оюутан",
        "ne": "विद्यार्थी",
        "th": "นักศึกษา",
        "tr": "Öğrenci",
        "uz": "Talaba",
        "vi": "Sinh viên",
    },
    Persona.ALUMNI: {
        "en": "Alumni",
        "ko": "졸업생",
        "zh-hans": "校友",
        "lo": "ສິດເກົ່າ",
        "de": "Alumni",
        "ru": "Выпускник",
        "ms": "Alumni",
        "fil": "Alumni",
        "fr": "Ancien étudiant",
        "ja": "卒業生",
        "mn": "Төгсөгч",
        "ne": "पूर्वविद्यार्थी",
        "th": "ศิษย์เก่า",
        "tr": "Mezun",
        "uz": "Bitiruvchi",
        "vi": "Cựu sinh viên",
    },
    Persona.INSTRUCTOR: {
        "en": "Instructor",
        "ko": "교원",
        "zh-hans": "教师",
        "lo": "ອາຈານ",
        "de": "Lehrperson",
        "ru": "Преподаватель",
        "ms": "Pensyarah",
        "fil": "Instruktor",
        "fr": "Enseignant",
        "ja": "教員",
        "mn": "Багш",
        "ne": "प्राध्यापक",
        "th": "อาจารย์",
        "tr": "Öğretim Elemanı",
        "uz": "Oʻqituvchi",
        "vi": "Giảng viên",
    },
    Persona.ADVISOR: {
        "en": "Advisor",
        "ko": "지도교수",
        "zh-hans": "指导教师",
        "lo": "ອາຈານທີ່ປຶກສາ",
        "de": "Mentor/in",
        "ru": "Куратор",
        "ms": "Penasihat akademik",
        "fil": "Tagapayo",
        "fr": "Enseignant référent",
        "ja": "指導教員",
        "mn": "Зөвлөх багш",
        "ne": "सल्लाहकार प्राध्यापक",
        "th": "อาจารย์ที่ปรึกษา",
        "tr": "Danışman",
        "uz": "Akademik maslahatchi",
        "vi": "Cố vấn học tập",
    },
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
