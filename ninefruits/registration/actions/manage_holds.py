"""Holds (legacy SRDENY) and overrides (legacy SRALLOW), with reasons, by staff with
``registration_holds.manage`` in a scope covering the student's record (original
``ManageHolds``)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.registration.enums import HoldSource, HoldType, RuleCode
from ninefruits.registration.models import RegistrationHold, RegistrationOverride
from ninefruits.security.enums import Permission
from ninefruits.security.services.authorization import authorization

from .enroll_student import now


def _seconds(value: datetime | None) -> datetime | None:
    return value.replace(microsecond=0) if value is not None else None


class ManageHolds:
    def place(
        self,
        record: Any,
        hold_type: HoldType | str,
        reason: str,
        staff: Any,
        *,
        blocks_registration: bool = True,
        blocks_grades: bool = False,
        blocks_certificates: bool = False,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        source: HoldSource | str = HoldSource.MANUAL,
    ) -> RegistrationHold:
        self._authorize(record, staff)
        hold_type = HoldType(hold_type)
        starts_at = _seconds(starts_at) or now()
        ends_at = _seconds(ends_at)
        if ends_at is not None and ends_at <= starts_at:
            raise ValidationError(
                {
                    "ends_at": _("The %(attribute)s field must be a date after %(date)s.")
                    % {"attribute": _("Ends"), "date": _("Starts")}
                }
            )
        hold = RegistrationHold.objects.create(
            student_record_id=record.pk,
            hold_type=hold_type,
            blocks_registration=blocks_registration,
            blocks_grades=blocks_grades,
            blocks_certificates=blocks_certificates,
            starts_at=starts_at,
            ends_at=ends_at,
            reason=reason,
            source=HoldSource(source),
            created_by_id=staff.pk,
        )
        audit("registration_hold.placed", hold, reason=reason, properties={"type": hold_type.value}, causer=staff)
        return hold

    def release(self, hold: RegistrationHold, reason: str, staff: Any) -> RegistrationHold:
        self._authorize(hold.student_record, staff)
        if hold.released_at is not None:
            raise ValidationError({"hold": _("This hold is already released.")})
        hold.released_at = now()
        hold.released_by_id = staff.pk
        hold.release_reason = reason
        hold.save(update_fields=["released_at", "released_by", "release_reason", "updated_at"])
        audit("registration_hold.released", hold, reason=reason, causer=staff)
        return hold

    def grant_override(
        self,
        record: Any,
        term: Any,
        rule: RuleCode | str,
        reason: str,
        staff: Any,
        *,
        section_id: int | None = None,
        course_id: int | None = None,
        expires_at: datetime | None = None,
    ) -> RegistrationOverride:
        self._authorize(record, staff)
        rule = RuleCode(rule)
        if rule.is_core() and rule != RuleCode.WINDOW:
            raise ValidationError({"rule_code": _("This rule cannot be overridden.")})
        override = RegistrationOverride.objects.create(
            student_record_id=record.pk,
            term_id=term.pk,
            rule_code=rule,
            section_id=section_id,
            course_id=course_id,
            reason=reason,
            expires_at=_seconds(expires_at),
            granted_by_id=staff.pk,
        )
        audit("registration_override.granted", override, reason=reason, properties={"rule": rule.value}, causer=staff)
        return override

    def revoke_override(self, override: RegistrationOverride, staff: Any) -> RegistrationOverride:
        self._authorize(override.student_record, staff)
        override.revoked_at = now()
        override.revoked_by_id = staff.pk
        override.save(update_fields=["revoked_at", "revoked_by", "updated_at"])
        audit("registration_override.revoked", override, causer=staff)
        return override

    def _authorize(self, record: Any, staff: Any) -> None:
        scope = authorization().scope_for(staff, Permission.REGISTRATION_HOLDS_MANAGE)
        if not scope.covers(record.org_unit_id, record.program_id):
            raise PermissionDenied
