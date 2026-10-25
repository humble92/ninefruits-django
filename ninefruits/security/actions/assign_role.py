from __future__ import annotations

from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.security.enums import Permission, ScopeType
from ninefruits.security.models import Role, RoleAssignment, User
from ninefruits.security.services.authorization import authorization, org_unit_descendant_ids


class AssignRole:
    """Grants a role to a user within a scope for a period (original ``AssignRole``)."""

    def __call__(
        self,
        user: User,
        role: Role,
        reason: str,
        scope_type: ScopeType = ScopeType.GLOBAL,
        scope_id: int | None = None,
        starts_at: datetime | None = None,
        ends_at: datetime | None = None,
        assigned_by: User | None = None,
        enforce_actor_limits: bool = True,
    ) -> RoleAssignment:
        scope_type = ScopeType(scope_type)
        # timestamp(0) columns hold whole seconds (the original wrote them that way).
        starts_at = starts_at.replace(microsecond=0) if starts_at else None
        ends_at = ends_at.replace(microsecond=0) if ends_at else None
        if role.is_persona():
            raise ValidationError({"role_id": _("Persona roles are granted automatically and cannot be assigned.")})
        if (scope_type == ScopeType.GLOBAL) != (scope_id is None):
            raise ValidationError(
                {"scope_id": _("Choose a scope target for scoped assignments, and none for global assignments.")}
            )
        if starts_at is not None and ends_at is not None and ends_at <= starts_at:
            raise ValidationError({"ends_at": _("The end must be after the start.")})
        if assigned_by is not None and enforce_actor_limits:
            self._guard_against_escalation(assigned_by, user, role, scope_type, scope_id)

        with transaction.atomic():
            assignment = RoleAssignment.objects.create(
                user=user,
                role=role,
                scope_type=scope_type,
                scope_id=scope_id,
                starts_at=starts_at,
                ends_at=ends_at,
                reason=reason,
                assigned_by=assigned_by,
            )
            properties = {
                "user_id": user.pk,
                "role": role.name,
                "scope_type": scope_type.value,
                "scope_id": scope_id,
                "starts_at": starts_at.isoformat() if starts_at else None,
                "ends_at": ends_at.isoformat() if ends_at else None,
            }
            audit("role.assigned", assignment, reason=reason, properties=properties, causer=assigned_by, log="security")
            record_security_event(
                SecurityEventType.ROLE_ASSIGNED, user=assigned_by, subject=assignment, properties=properties
            )
        authorization().flush()
        return assignment

    def _guard_against_escalation(
        self, actor: User, user: User, role: Role, scope_type: ScopeType, scope_id: int | None
    ) -> None:
        """Nobody grants themselves a role, a role with permissions they do not hold, or a scope
        wider than their own ``role_assignments.manage`` scope (security review H3)."""
        if actor.pk == user.pk:
            raise ValidationError({"user_id": _("You cannot assign a role to yourself.")})
        missing = [name for name in role.permission_names() if not actor.has_perm(name)]
        if missing:
            raise ValidationError(
                {
                    "role_id": _("This role carries permissions you do not hold (%(permissions)s).")
                    % {"permissions": ", ".join(missing[:3])}
                }
            )
        scope = authorization().scope_for(actor, Permission.ROLE_ASSIGNMENTS_MANAGE)
        if scope.is_global:
            return
        match scope_type:
            case ScopeType.GLOBAL:
                allowed = False
            case ScopeType.ORG_UNIT:
                allowed = scope_id in scope.org_unit_ids or scope_id in org_unit_descendant_ids(scope.org_unit_ids)
            case ScopeType.PROGRAM:
                allowed = scope_id in scope.program_ids
        if not allowed:
            raise ValidationError({"scope_id": _("This scope is wider than the one you manage role assignments for.")})
