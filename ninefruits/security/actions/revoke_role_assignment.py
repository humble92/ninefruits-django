from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from ninefruits.audit.logger import audit
from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.security.models import RoleAssignment, User
from ninefruits.security.services.authorization import authorization


class RevokeRoleAssignment:
    """Ends an assignment now and keeps the row as history. An assignment that has not started
    yet is deleted (the audit trigger keeps its record)."""

    def __call__(self, assignment: RoleAssignment, reason: str, revoked_by: User | None = None) -> RoleAssignment:
        # timestamp(0) columns: whole seconds, as the original wrote them (rounding could leave
        # the assignment active for up to half a second).
        now = timezone.now().replace(microsecond=0)
        with transaction.atomic():
            properties = {"user_id": assignment.user_id, "role_id": assignment.role_id}
            if assignment.starts_at is not None and assignment.starts_at >= now:
                assignment_id = assignment.pk
                assignment.delete()
                assignment.pk = assignment_id
            else:
                assignment.ends_at = now
                assignment.save(update_fields=["ends_at", "updated_at"])
            audit(
                "role.assignment_revoked",
                assignment,
                reason=reason,
                properties=properties,
                causer=revoked_by,
                log="security",
            )
            record_security_event(
                SecurityEventType.ROLE_ASSIGNMENT_REVOKED, user=revoked_by, subject=assignment, properties=properties
            )
        authorization().flush()
        return assignment
