"""Reference data policies (original ``App\\Policies\\Reference\\*``).

Anyone with ``reference_data.view`` can look; the resource's manage permission is needed to
change. Each app registers its models with the manage permission of the original policy."""

from __future__ import annotations

from typing import Any

from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class ReferenceDataPolicy(Policy):
    def __init__(self, manage_permission: Permission) -> None:
        self.manage_permission = manage_permission

    def _can_manage(self, user: Any) -> bool:
        return bool(user.has_perm(self.manage_permission))

    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.REFERENCE_DATA_VIEW)) or self._can_manage(user)

    def view(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)

    def create(self, user: Any, obj: Any) -> bool:
        return self._can_manage(user)

    def update(self, user: Any, obj: Any) -> bool:
        return self._can_manage(user)

    def delete(self, user: Any, obj: Any) -> bool:
        return self._can_manage(user)

    def delete_any(self, user: Any, obj: Any) -> bool:
        return self._can_manage(user)


#: Model label -> manage permission (original ``AppServiceProvider::$policies``).
REFERENCE_POLICIES: dict[str, Permission] = {
    "institution.country": Permission.LOOKUP_VALUES_MANAGE,
    "institution.language": Permission.LOOKUP_VALUES_MANAGE,
    "institution.lookuptype": Permission.LOOKUP_VALUES_MANAGE,
    "institution.lookupvalue": Permission.LOOKUP_VALUES_MANAGE,
    "organization.orgunittype": Permission.ORG_UNITS_MANAGE,
    "organization.orgunit": Permission.ORG_UNITS_MANAGE,
    "organization.orgunitsuccession": Permission.ORG_UNITS_MANAGE,
    "organization.program": Permission.PROGRAMS_MANAGE,
    "facility.building": Permission.FACILITIES_MANAGE,
    "facility.room": Permission.FACILITIES_MANAGE,
    "term.termtype": Permission.TERMS_MANAGE,
    "term.academicyear": Permission.TERMS_MANAGE,
    "term.term": Permission.TERMS_MANAGE,
    "term.timeslot": Permission.TERMS_MANAGE,
    "term.termsession": Permission.TERMS_MANAGE,
    "term.termwindow": Permission.TERM_WINDOWS_MANAGE,
    "curriculum.coursecategory": Permission.COURSE_CATEGORIES_MANAGE,
    "grading.gradescale": Permission.GRADE_SCALES_MANAGE,
    "grading.gradescaleitem": Permission.GRADE_SCALES_MANAGE,
}


def register_reference_policies(app_label: str) -> None:
    for label, permission in REFERENCE_POLICIES.items():
        if label.split(".", 1)[0] == app_label:
            register(label, ReferenceDataPolicy(permission))
