"""Security enums (original ``App\\Domain\\Security\\Enums``).

``Permission`` is the permission catalog. Naming: ``{resource}.{action}``, resource in
snake_case plural. ``security_sync_permissions`` keeps the ``permissions`` table in step with
this enum. ``SecurityEventType`` lives in ``ninefruits.audit.security_events``."""

from __future__ import annotations

from enum import StrEnum

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class Permission(StrEnum):
    ADMIN_PANEL_ACCESS = "admin_panel.access"
    USERS_VIEW = "users.view"
    USERS_CREATE = "users.create"
    USERS_UPDATE = "users.update"
    USERS_RESET_MFA = "users.reset_mfa"
    ROLES_VIEW = "roles.view"
    ROLES_MANAGE = "roles.manage"
    ROLE_ASSIGNMENTS_MANAGE = "role_assignments.manage"
    AUDIT_RECORDS_VIEW = "audit_records.view"
    SECURITY_EVENTS_VIEW = "security_events.view"
    SECURITY_SETTINGS_MANAGE = "security_settings.manage"
    INSTITUTION_SETTINGS_MANAGE = "institution_settings.manage"
    QUEUE_MONITOR_VIEW = "queue_monitor.view"
    REFERENCE_DATA_VIEW = "reference_data.view"
    REFERENCE_DATA_IMPORT = "reference_data.import"
    LOOKUP_VALUES_MANAGE = "lookup_values.manage"
    ORG_UNITS_MANAGE = "org_units.manage"
    PROGRAMS_MANAGE = "programs.manage"
    FACILITIES_MANAGE = "facilities.manage"
    TERMS_MANAGE = "terms.manage"
    TERM_WINDOWS_MANAGE = "term_windows.manage"
    COURSE_CATEGORIES_MANAGE = "course_categories.manage"
    GRADE_SCALES_MANAGE = "grade_scales.manage"
    PEOPLE_VIEW = "people.view"
    PEOPLE_MANAGE = "people.manage"
    PEOPLE_VIEW_SENSITIVE = "people.view_sensitive"
    PEOPLE_MERGE = "people.merge"
    ACCOUNTS_INVITE = "accounts.invite"
    STUDENT_RECORDS_VIEW = "student_records.view"
    STUDENT_RECORDS_MANAGE = "student_records.manage"
    STUDENT_STATUS_CHANGES_APPROVE = "student_status_changes.approve"
    INSTRUCTORS_MANAGE = "instructors.manage"
    ADVISORS_MANAGE = "advisors.manage"
    AUTHENTICATION_SETTINGS_MANAGE = "authentication_settings.manage"
    ADMISSION_CYCLES_MANAGE = "admission_cycles.manage"
    APPLICATIONS_VIEW = "applications.view"
    APPLICATIONS_REVIEW = "applications.review"
    APPLICATIONS_MATRICULATE = "applications.matriculate"
    COURSES_MANAGE = "courses.manage"
    CURRICULUM_MANAGE = "curriculum.manage"
    SECTIONS_VIEW = "sections.view"
    SECTIONS_MANAGE = "sections.manage"
    ADDITIONAL_PROGRAMS_APPROVE = "additional_programs.approve"
    ENROLLMENTS_VIEW = "enrollments.view"
    REGISTRATION_MANAGE = "registration.manage"
    REGISTRATION_RULES_MANAGE = "registration_rules.manage"
    REGISTRATION_HOLDS_MANAGE = "registration_holds.manage"
    GRADES_VIEW = "grades.view"
    GRADES_MANAGE = "grades.manage"
    GRADE_CHANGES_REQUEST = "grade_changes.request"
    GRADE_CHANGES_APPROVE = "grade_changes.approve"
    GRADING_POLICIES_MANAGE = "grading_policies.manage"
    GRADE_EXCEPTIONS_REVIEW = "grade_exceptions.review"
    EVALUATIONS_VIEW = "evaluations.view"
    EVALUATIONS_MANAGE = "evaluations.manage"
    CERTIFICATES_ISSUE = "certificates.issue"
    CERTIFICATES_MANAGE = "certificates.manage"
    ASSESSMENTS_RECORD = "assessments.record"
    ASSESSMENTS_MANAGE = "assessments.manage"
    GRADUATION_AUDIT = "graduation.audit"
    GRADUATION_PROCESS = "graduation.process"
    REPORTS_VIEW = "reports.view"
    LMS_MANAGE = "lms.manage"

    @property
    def resource(self) -> str:
        return self.value.split(".", 1)[0]

    @property
    def label(self) -> str:
        return str(PERMISSION_LABELS.get(self, self.value))

    @classmethod
    def grouped_by_resource(cls) -> dict[str, list[Permission]]:
        """Catalog order, one entry per resource (original ``groupedByResource``)."""
        groups: dict[str, list[Permission]] = {}
        for permission in cls:
            groups.setdefault(permission.resource, []).append(permission)
        return groups

    @staticmethod
    def resource_label(resource: str) -> str:
        return str(RESOURCE_LABELS.get(resource, resource))


# The "permissions" context: catalog labels are translated apart from the same words elsewhere.
RESOURCE_LABELS: dict[str, object] = {
    "people": pgettext_lazy("permissions", "People"),
    "accounts": pgettext_lazy("permissions", "Accounts"),
    "student_records": pgettext_lazy("permissions", "Student records"),
    "student_status_changes": pgettext_lazy("permissions", "Status changes"),
    "instructors": pgettext_lazy("permissions", "Instructors"),
    "advisors": pgettext_lazy("permissions", "Advisors"),
    "authentication_settings": pgettext_lazy("permissions", "Sign-in settings"),
    "reference_data": pgettext_lazy("permissions", "Reference data"),
    "lookup_values": pgettext_lazy("permissions", "Code data"),
    "org_units": pgettext_lazy("permissions", "Org units"),
    "programs": pgettext_lazy("permissions", "Programs"),
    "facilities": pgettext_lazy("permissions", "Buildings and rooms"),
    "terms": pgettext_lazy("permissions", "Academic years and terms"),
    "term_windows": pgettext_lazy("permissions", "Term windows"),
    "course_categories": pgettext_lazy("permissions", "Course categories"),
    "grade_scales": pgettext_lazy("permissions", "Grade scales"),
    "admin_panel": pgettext_lazy("permissions", "Administration panel"),
    "users": pgettext_lazy("permissions", "Users"),
    "roles": pgettext_lazy("permissions", "Roles"),
    "role_assignments": pgettext_lazy("permissions", "Role assignments"),
    "audit_records": pgettext_lazy("permissions", "Audit records"),
    "security_events": pgettext_lazy("permissions", "Security events"),
    "security_settings": pgettext_lazy("permissions", "Security settings"),
    "queue_monitor": pgettext_lazy("permissions", "Queue monitor (Flower)"),
    "institution_settings": pgettext_lazy("permissions", "Institution settings"),
    "admission_cycles": pgettext_lazy("permissions", "Admission cycles"),
    "applications": pgettext_lazy("permissions", "Applications"),
    "courses": pgettext_lazy("permissions", "Courses"),
    "curriculum": pgettext_lazy("permissions", "Graduation requirements"),
    "sections": pgettext_lazy("permissions", "Sections"),
    "additional_programs": pgettext_lazy("permissions", "Second majors and minors"),
    "enrollments": pgettext_lazy("permissions", "Registrations"),
    "registration": pgettext_lazy("permissions", "Registration adjustments"),
    "registration_rules": pgettext_lazy("permissions", "Registration rules"),
    "registration_holds": pgettext_lazy("permissions", "Registration holds and overrides"),
    "grades": pgettext_lazy("permissions", "Grades"),
    "grade_changes": pgettext_lazy("permissions", "Grade changes"),
    "grading_policies": pgettext_lazy("permissions", "Grading policy"),
    "grade_exceptions": pgettext_lazy("permissions", "Grade exceptions"),
    "evaluations": pgettext_lazy("permissions", "Course evaluation"),
    "assessments": pgettext_lazy("permissions", "Examinations"),
    "graduation": pgettext_lazy("permissions", "Graduation"),
    "reports": pgettext_lazy("permissions", "Reports"),
    "lms": pgettext_lazy("permissions", "LMS integration"),
    "certificates": pgettext_lazy("permissions", "Certificates"),
}

PERMISSION_LABELS: dict[Permission, object] = {
    Permission.ADMIN_PANEL_ACCESS: pgettext_lazy("permissions", "Open the administration panel"),
    Permission.USERS_VIEW: pgettext_lazy("permissions", "View users"),
    Permission.USERS_CREATE: pgettext_lazy("permissions", "Create users"),
    Permission.USERS_UPDATE: pgettext_lazy("permissions", "Edit users"),
    Permission.USERS_RESET_MFA: pgettext_lazy("permissions", "Reset two-factor authentication"),
    Permission.ROLES_VIEW: pgettext_lazy("permissions", "View roles"),
    Permission.ROLES_MANAGE: pgettext_lazy("permissions", "Create and edit roles"),
    Permission.ROLE_ASSIGNMENTS_MANAGE: pgettext_lazy("permissions", "Assign and end roles"),
    Permission.AUDIT_RECORDS_VIEW: pgettext_lazy("permissions", "View audit records"),
    Permission.SECURITY_EVENTS_VIEW: pgettext_lazy("permissions", "View security events"),
    Permission.SECURITY_SETTINGS_MANAGE: pgettext_lazy("permissions", "Manage security settings"),
    Permission.INSTITUTION_SETTINGS_MANAGE: pgettext_lazy("permissions", "Manage institution settings"),
    Permission.QUEUE_MONITOR_VIEW: pgettext_lazy("permissions", "View the queue monitor"),
    Permission.REFERENCE_DATA_VIEW: pgettext_lazy("permissions", "View reference data"),
    Permission.REFERENCE_DATA_IMPORT: pgettext_lazy("permissions", "Import reference data from CSV"),
    Permission.LOOKUP_VALUES_MANAGE: pgettext_lazy("permissions", "Manage code data, countries and languages"),
    Permission.ORG_UNITS_MANAGE: pgettext_lazy("permissions", "Manage org units and reorganizations"),
    Permission.PROGRAMS_MANAGE: pgettext_lazy("permissions", "Manage programs"),
    Permission.FACILITIES_MANAGE: pgettext_lazy("permissions", "Manage buildings and rooms"),
    Permission.TERMS_MANAGE: pgettext_lazy("permissions", "Manage academic years, terms, term types and time slots"),
    Permission.TERM_WINDOWS_MANAGE: pgettext_lazy("permissions", "Manage term windows"),
    Permission.COURSE_CATEGORIES_MANAGE: pgettext_lazy("permissions", "Manage course categories"),
    Permission.GRADE_SCALES_MANAGE: pgettext_lazy("permissions", "Manage grade scales"),
    Permission.PEOPLE_VIEW: pgettext_lazy("permissions", "View all people"),
    Permission.PEOPLE_MANAGE: pgettext_lazy("permissions", "Create and edit people"),
    Permission.PEOPLE_VIEW_SENSITIVE: pgettext_lazy("permissions", "Reveal national ID and passport numbers"),
    Permission.PEOPLE_MERGE: pgettext_lazy("permissions", "Merge duplicate people"),
    Permission.ACCOUNTS_INVITE: pgettext_lazy("permissions", "Invite people to create an account"),
    Permission.STUDENT_RECORDS_VIEW: pgettext_lazy("permissions", "View student records"),
    Permission.STUDENT_RECORDS_MANAGE: pgettext_lazy("permissions", "Create and edit student records"),
    Permission.STUDENT_STATUS_CHANGES_APPROVE: pgettext_lazy("permissions", "Approve and record status changes"),
    Permission.INSTRUCTORS_MANAGE: pgettext_lazy("permissions", "Manage instructors"),
    Permission.ADVISORS_MANAGE: pgettext_lazy("permissions", "Assign advisors"),
    Permission.AUTHENTICATION_SETTINGS_MANAGE: pgettext_lazy("permissions", "Manage sign-in methods and SSO"),
    Permission.ADMISSION_CYCLES_MANAGE: pgettext_lazy("permissions", "Manage admission cycles and admission settings"),
    Permission.APPLICATIONS_VIEW: pgettext_lazy("permissions", "View applications"),
    Permission.APPLICATIONS_REVIEW: pgettext_lazy("permissions", "Review and decide applications"),
    Permission.APPLICATIONS_MATRICULATE: pgettext_lazy("permissions", "Create student records for admitted applicants"),
    Permission.COURSES_MANAGE: pgettext_lazy("permissions", "Manage courses, versions and requisites"),
    Permission.CURRICULUM_MANAGE: pgettext_lazy("permissions", "Manage graduation requirements"),
    Permission.SECTIONS_VIEW: pgettext_lazy("permissions", "View sections"),
    Permission.SECTIONS_MANAGE: pgettext_lazy("permissions", "Plan sections (instructors, times, rooms)"),
    Permission.ADDITIONAL_PROGRAMS_APPROVE: pgettext_lazy("permissions", "Decide second major and minor applications"),
    Permission.ENROLLMENTS_VIEW: pgettext_lazy("permissions", "View registrations and rosters"),
    Permission.REGISTRATION_MANAGE: pgettext_lazy(
        "permissions", "Register, drop and withdraw students for them (with a reason)"
    ),
    Permission.REGISTRATION_RULES_MANAGE: pgettext_lazy(
        "permissions", "Manage registration rule sets and credit limits"
    ),
    Permission.REGISTRATION_HOLDS_MANAGE: pgettext_lazy("permissions", "Place and release holds, grant rule overrides"),
    Permission.GRADES_VIEW: pgettext_lazy("permissions", "View grades, grade progress and term records"),
    Permission.GRADES_MANAGE: pgettext_lazy(
        "permissions", "Finalize and return grades, enter grades for instructors, close terms"
    ),
    Permission.GRADE_CHANGES_REQUEST: pgettext_lazy("permissions", "Request a change to a finalized grade"),
    Permission.GRADE_CHANGES_APPROVE: pgettext_lazy(
        "permissions", "Approve or reject grade changes (not your own requests)"
    ),
    Permission.GRADING_POLICIES_MANAGE: pgettext_lazy(
        "permissions", "Manage GPA, retake, academic standing and honors policy"
    ),
    Permission.GRADE_EXCEPTIONS_REVIEW: pgettext_lazy(
        "permissions", "Be told when staff submit grades outside the grade caps (department heads, academic office)"
    ),
    Permission.EVALUATIONS_VIEW: pgettext_lazy("permissions", "View course evaluation response rates and results"),
    Permission.EVALUATIONS_MANAGE: pgettext_lazy(
        "permissions", "Manage evaluation forms, term evaluations and publication"
    ),
    Permission.CERTIFICATES_ISSUE: pgettext_lazy("permissions", "Issue, re-render and revoke certificates"),
    Permission.CERTIFICATES_MANAGE: pgettext_lazy("permissions", "Manage certificate kinds, templates and settings"),
    Permission.ASSESSMENTS_RECORD: pgettext_lazy(
        "permissions", "Register students, enter and publish results, record external results"
    ),
    Permission.ASSESSMENTS_MANAGE: pgettext_lazy("permissions", "Manage examination kinds, areas and sessions"),
    Permission.GRADUATION_AUDIT: pgettext_lazy("permissions", "Run and view degree audits"),
    Permission.GRADUATION_PROCESS: pgettext_lazy("permissions", "Process graduations, grant requirement waivers"),
    Permission.REPORTS_VIEW: pgettext_lazy("permissions", "View standard reports and download them"),
    Permission.LMS_MANAGE: pgettext_lazy("permissions", "Manage LMS platforms, links and synchronization"),
}


class _LabelledEnum(StrEnum):
    """String enum whose members have a translated ``label`` (original ``label()``)."""

    @property
    def label(self) -> str:
        return str(_LABELS[type(self).__name__].get(self.value, self.value))

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        return [(member.value, member.label) for member in cls]


class MfaEnforcement(_LabelledEnum):
    DISABLED = "disabled"
    RECOMMENDED = "recommended"
    REQUIRED_FOR_ROLES = "required_for_roles"
    REQUIRED_FOR_ALL = "required_for_all"


class MfaMethod(_LabelledEnum):
    AUTHENTICATOR_APP = "authenticator_app"
    EMAIL_CODE = "email_code"


class MfaRequirement(StrEnum):
    NONE = "none"
    RECOMMENDED = "recommended"
    REQUIRED = "required"


class Persona(_LabelledEnum):
    """Identity based roles granted from data, never assigned by hand (porting-plan 7.2)."""

    APPLICANT = "applicant"
    STUDENT = "student"
    ALUMNI = "alumni"
    INSTRUCTOR = "instructor"
    ADVISOR = "advisor"


class ScopeType(_LabelledEnum):
    GLOBAL = "global"
    ORG_UNIT = "org_unit"
    PROGRAM = "program"


class SsoLinkMode(_LabelledEnum):
    """How a school account is linked on its first SSO sign-in."""

    MANUAL = "manual"
    INSTITUTIONAL_EMAIL = "institutional_email"


class StudentNumberLogin(_LabelledEnum):
    """Whether a student number can be used instead of the email to sign in."""

    DISABLED = "disabled"
    ACTIVE_RECORDS = "active_records"
    ALL_RECORDS = "all_records"


_LABELS: dict[str, dict[str, object]] = {
    "MfaEnforcement": {
        "disabled": _("Not used"),
        "recommended": _("Recommended (optional)"),
        "required_for_roles": _("Required for selected roles"),
        "required_for_all": _("Required for everyone"),
    },
    "MfaMethod": {
        "authenticator_app": _("Authenticator app"),
        "email_code": _("Email code"),
    },
    "Persona": {
        "applicant": pgettext_lazy("security", "Applicant"),
        "student": pgettext_lazy("security", "Student"),
        "alumni": pgettext_lazy("security", "Alumni"),
        "instructor": pgettext_lazy("security", "Instructor"),
        "advisor": pgettext_lazy("security", "Advisor"),
    },
    "ScopeType": {
        "global": pgettext_lazy("security", "All"),
        "org_unit": pgettext_lazy("security", "Org unit"),
        "program": pgettext_lazy("security", "Program"),
    },
    "SsoLinkMode": {
        "manual": _("Users link their own accounts"),
        "institutional_email": _("Link automatically by verified school email"),
    },
    "StudentNumberLogin": {
        "disabled": _("Not allowed"),
        "active_records": _("Current students only"),
        "all_records": _("Current students and graduates"),
    },
}
