"""Merging duplicate people (original ``MergePeople``, ADR 0007)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.core.db import session_context
from ninefruits.person.models import AccountInvitation, Guardian, Instructor, Person, StudentRecord
from ninefruits.security.enums import Permission
from ninefruits.security.models import User, UserIdentity

_COPIED_FIELDS = ("email", "phone", "address", "postal_code", "birth_date", "gender", "nationality_id", "ethnicity_id")
_COPIED_PII = ("national_id_encrypted", "passport_number_encrypted")


def _open_application_cycles(person: Person) -> set[int]:
    """Admission cycles in which the person has an open application (the table exists from
    the replayed schema; the model arrives in Phase 3)."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT admission_cycle_id FROM applications WHERE person_id = %s "
            "AND status NOT IN ('withdrawn', 'rejected', 'expired')",
            [person.pk],
        )
        return {int(row[0]) for row in cursor.fetchall()}


def _move_applications(duplicate: Person, target: Person) -> int:
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("UPDATE applications SET person_id = %s WHERE person_id = %s", [target.pk, duplicate.pk])
        return int(cursor.rowcount)


class MergePeople:
    """Merges a duplicate person into another: student records, applications, guardians, the
    instructor record and the account move to the target; the duplicate stays as a pointer
    (``merged_into_person_id``) so old references resolve. When both have an account, the
    duplicate's account is deactivated and its SSO identities move where possible."""

    def handle(self, duplicate: Person, target: Person, reason: str, merged_by: Any) -> Person:
        if not merged_by.has_perm(Permission.PEOPLE_MERGE) or not merged_by.has_perm(Permission.PEOPLE_MANAGE):
            raise PermissionDenied
        if duplicate.pk == target.pk or duplicate.merged_into_id is not None or target.merged_into_id is not None:
            raise ValidationError({"target_id": _("Choose a different person who has not been merged.")})
        if Instructor.objects.filter(person=duplicate).exists() and Instructor.objects.filter(person=target).exists():
            raise ValidationError(
                {"target_id": _("Both people have instructor records. Merge the instructor records first.")}
            )
        context = session_context()
        # Staff who merge people may not see applications; the check and the move are part of
        # the merge, which was authorized above.
        with context.system("person_merge"):
            shared_cycles = _open_application_cycles(duplicate) & _open_application_cycles(target)
        if shared_cycles:
            raise ValidationError(
                {
                    "target_id": _(
                        "Both people have an open application in the same admission cycle. Withdraw one first."
                    )
                }
            )

        with transaction.atomic():
            moved: dict[str, Any] = {
                "student_records": StudentRecord.objects.filter(person=duplicate).update(person=target),
                "guardians": Guardian.objects.filter(person=duplicate).update(person=target),
                "instructor": Instructor.objects.filter(person=duplicate).update(person=target),
            }
            with context.system("person_merge"):
                moved["applications"] = _move_applications(duplicate, target)
            moved["invitations"] = AccountInvitation.objects.filter(
                person=duplicate, accepted_at__isnull=True
            ).delete()[0]

            for field in _COPIED_FIELDS:
                if getattr(target, field) is None and getattr(duplicate, field) is not None:
                    setattr(target, field, getattr(duplicate, field))
            for field in _COPIED_PII:
                if getattr(target, field) is None and getattr(duplicate, field) is not None:
                    setattr(target, field, getattr(duplicate, field))
            variants = {**(duplicate.name_variants or {}), **(target.name_variants or {})}
            target.name_variants = variants or None
            target.save()

            moved["account"] = self._move_account(duplicate, target)

            duplicate.merged_into = target
            duplicate.save(update_fields=["merged_into", "updated_at"])

            audit(
                "person.merged",
                target,
                reason=reason,
                properties={"duplicate_person_id": duplicate.pk, "moved": moved},
                causer=merged_by,
            )
        return target

    __call__ = handle

    @staticmethod
    def _move_account(duplicate: Person, target: Person) -> str:
        duplicate_user = User.objects.filter(person_id=duplicate.pk).first()
        if duplicate_user is None:
            return "none"
        target_user = User.objects.filter(person_id=target.pk).first()
        if target_user is None:
            duplicate_user.person = target
            duplicate_user.save(update_fields=["person", "updated_at"])
            return "moved"
        for identity in UserIdentity.objects.filter(user=duplicate_user):
            if not UserIdentity.objects.filter(user=target_user, provider=identity.provider).exists():
                identity.user = target_user
                identity.save(update_fields=["user", "updated_at"])
        duplicate_user.person = None
        duplicate_user.is_active = False
        duplicate_user.save(update_fields=["person", "is_active", "updated_at"])
        return "deactivated"
