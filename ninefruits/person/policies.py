"""Person policies (original ``App\\Policies\\Person\\*`` and ``StatusChangeTypePolicy``).
Registered from ``PersonConfig.ready``."""

from __future__ import annotations

from typing import Any

from ninefruits.institution.policies import ReferenceDataPolicy
from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class PersonPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(
            user.has_perm(Permission.PEOPLE_VIEW)
            or user.has_perm(Permission.STUDENT_RECORDS_VIEW)
            or user.has_perm(Permission.STUDENT_RECORDS_MANAGE)
        )

    def view(self, user: Any, obj: Any) -> bool:
        return obj is not None and obj.is_visible_to(user)

    def create(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.PEOPLE_MANAGE) or user.has_perm(Permission.STUDENT_RECORDS_MANAGE))

    def update(self, user: Any, obj: Any) -> bool:
        if obj is None:
            return False
        if user.has_perm(Permission.PEOPLE_MANAGE) or obj.created_by_id == user.pk:
            return True
        return any(record.is_manageable_by(user) for record in obj.student_records.all())

    def view_sensitive(self, user: Any, obj: Any) -> bool:
        return user.has_perm(Permission.PEOPLE_VIEW_SENSITIVE) and self.view(user, obj)

    def merge(self, user: Any, obj: Any) -> bool:
        return (
            user.has_perm(Permission.PEOPLE_MERGE)
            and user.has_perm(Permission.PEOPLE_MANAGE)
            and obj is not None
            and obj.merged_into_id is None
        )

    def invite(self, user: Any, obj: Any) -> bool:
        return user.has_perm(Permission.ACCOUNTS_INVITE) and self.view(user, obj)

    def delete(self, user: Any, obj: Any) -> bool:
        return False


class GuardianPolicy(Policy):
    """Guardians are managed on the person (same rules as updating the person)."""

    def view(self, user: Any, obj: Any) -> bool:
        return obj is not None and PersonPolicy().view(user, obj.person)

    def update(self, user: Any, obj: Any) -> bool:
        return obj is not None and PersonPolicy().update(user, obj.person)

    def delete(self, user: Any, obj: Any) -> bool:
        return self.update(user, obj)


class StudentRecordPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.STUDENT_RECORDS_VIEW) or user.has_perm(Permission.STUDENT_RECORDS_MANAGE))

    def view(self, user: Any, obj: Any) -> bool:
        return obj is not None and obj.is_visible_to(user)

    def create(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.STUDENT_RECORDS_MANAGE))

    def update(self, user: Any, obj: Any) -> bool:
        return obj is not None and obj.is_manageable_by(user)

    def change_status(self, user: Any, obj: Any) -> bool:
        return user.has_perm(Permission.STUDENT_STATUS_CHANGES_APPROVE) and obj is not None and obj.is_visible_to(user)

    def assign_advisor(self, user: Any, obj: Any) -> bool:
        return user.has_perm(Permission.ADVISORS_MANAGE) and obj is not None and obj.is_visible_to(user)

    def delete(self, user: Any, obj: Any) -> bool:
        """Student records are never deleted; status changes end them."""
        return False


class StudentStatusChangePolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(
            user.has_perm(Permission.STUDENT_STATUS_CHANGES_APPROVE) or user.has_perm(Permission.STUDENT_RECORDS_VIEW)
        )

    def view(self, user: Any, obj: Any) -> bool:
        return obj is not None and obj.student_record.is_visible_to(user)

    def decide(self, user: Any, obj: Any) -> bool:
        """Requesters cannot decide their own request (separation of duties)."""
        return (
            user.has_perm(Permission.STUDENT_STATUS_CHANGES_APPROVE)
            and obj is not None
            and obj.requested_by_id != user.pk
            and self.view(user, obj)
        )

    def create(self, user: Any, obj: Any) -> bool:
        return False

    def update(self, user: Any, obj: Any) -> bool:
        return False

    def delete(self, user: Any, obj: Any) -> bool:
        return False


class InstructorPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(
            user.has_perm(Permission.INSTRUCTORS_MANAGE)
            or user.has_perm(Permission.PEOPLE_VIEW)
            or user.has_perm(Permission.ADVISORS_MANAGE)
        )

    def view(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)

    def create(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.INSTRUCTORS_MANAGE))

    def update(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.INSTRUCTORS_MANAGE))

    def delete(self, user: Any, obj: Any) -> bool:
        return False


class AdditionalProgramRequestPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(
            user.has_perm(Permission.ADDITIONAL_PROGRAMS_APPROVE)
            or user.has_perm(Permission.STUDENT_RECORDS_VIEW)
            or user.has_perm(Permission.STUDENT_RECORDS_MANAGE)
        )

    def decide(self, user: Any, obj: Any) -> bool:
        return obj is not None and obj.is_decidable_by(user)

    def create(self, user: Any, obj: Any) -> bool:
        return False


def register_person_policies() -> None:
    register("person.person", PersonPolicy())
    register("person.guardian", GuardianPolicy())
    register("person.studentrecord", StudentRecordPolicy())
    register("person.studentstatuschange", StudentStatusChangePolicy())
    register("person.instructor", InstructorPolicy())
    register("person.additionalprogramrequest", AdditionalProgramRequestPolicy())
    register("person.studentstatuschangetype", ReferenceDataPolicy(Permission.STUDENT_RECORDS_MANAGE))
