"""Model policies (original ``App\\Policies\\UserPolicy`` and ``App\\Policies\\Security\\*``).

``user.has_perm(ability, obj)`` reaches ``policy_for(obj)``: ``has_perm("revoke", assignment)``
calls ``RoleAssignmentPolicy.revoke(user, assignment)``. ``obj`` may also be a model class for
abilities without a record (``has_perm("create", RoleAssignment)``). Catalog permission names
are answered by ``AuthorizationService`` first (original ``Gate::before``), see
``ninefruits.security.backends``. Other apps register their policies with ``register``::

    from ninefruits.security.policies import register
    register("person.person", PersonPolicy())
"""

from __future__ import annotations

from typing import Any

from django.db import models

from ninefruits.security.enums import Permission


class Policy:
    """Base: an ability is a method ``(user, obj) -> bool``; missing abilities are denied."""

    def allows(self, user: Any, ability: str, obj: Any) -> bool:
        method = getattr(self, ability, None)
        if method is None or ability.startswith("_") or ability == "allows":
            return False
        return bool(method(user, None if isinstance(obj, type) else obj))


class UserPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.USERS_VIEW))

    def view(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.USERS_VIEW))

    def create(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.USERS_CREATE))

    def update(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.USERS_UPDATE))

    def unlock(self, user: Any, obj: Any) -> bool:
        return user.has_perm(Permission.USERS_UPDATE) and obj is not None and user.pk != obj.pk

    def reset_mfa(self, user: Any, obj: Any) -> bool:
        return user.has_perm(Permission.USERS_RESET_MFA) and obj is not None and user.pk != obj.pk

    def delete(self, user: Any, obj: Any) -> bool:
        """Accounts are deactivated, not deleted, so their history stays attached."""
        return False


class RolePolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.ROLES_VIEW))

    def view(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.ROLES_VIEW))

    def create(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.ROLES_MANAGE))

    def update(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.ROLES_MANAGE))

    def delete(self, user: Any, obj: Any) -> bool:
        return (
            user.has_perm(Permission.ROLES_MANAGE)
            and obj is not None
            and not obj.is_system
            and not obj.is_persona()
            and not obj.assignments.exists()
        )


class RoleAssignmentPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.USERS_VIEW))

    def create(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.ROLE_ASSIGNMENTS_MANAGE))

    def revoke(self, user: Any, obj: Any) -> bool:
        """Ending an assignment. Users cannot change their own assignments (separation of duties)."""
        return (
            user.has_perm(Permission.ROLE_ASSIGNMENTS_MANAGE)
            and obj is not None
            and obj.user_id != user.pk
            and obj.is_active()
        )


class AuditRecordPolicy(Policy):
    """Activity log and record changes. Audit records are read only."""

    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.AUDIT_RECORDS_VIEW))

    def view(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.AUDIT_RECORDS_VIEW))


class SecurityEventPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.SECURITY_EVENTS_VIEW))

    def view(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.SECURITY_EVENTS_VIEW))


_registry: dict[str, Policy] = {
    "security.user": UserPolicy(),
    "security.role": RolePolicy(),
    "security.roleassignment": RoleAssignmentPolicy(),
    "audit.activity": AuditRecordPolicy(),
    "audit.activitylog": AuditRecordPolicy(),
    "audit.recordchange": AuditRecordPolicy(),
    "audit.securityevent": SecurityEventPolicy(),
}


def register(model_label: str, policy: Policy) -> None:
    _registry[model_label.lower()] = policy


def policy_for(obj: Any) -> Policy | None:
    model = obj if isinstance(obj, type) else type(obj)
    if not (isinstance(model, type) and issubclass(model, models.Model)):
        return None
    return _registry.get(model._meta.label_lower)
