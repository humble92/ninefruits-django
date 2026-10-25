from __future__ import annotations

from django.db import transaction

from ninefruits.audit.logger import audit
from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.security.models import Permission, Role, User
from ninefruits.security.services.authorization import authorization


class UpdateRolePermissions:
    """Replaces a role's permissions, audited with what was added and removed."""

    def __call__(
        self, role: Role, permission_names: list[str], changed_by: User | None = None, reason: str | None = None
    ) -> Role:
        before = role.permission_names()
        after = sorted(Permission.objects.filter(name__in=permission_names).values_list("name", flat=True))
        if before == after:
            return role
        with transaction.atomic():
            role.sync_permissions(after)
            properties = {
                "added": [name for name in after if name not in before],
                "removed": [name for name in before if name not in after],
            }
            audit(
                "role.permissions_changed",
                role,
                reason=reason,
                properties=properties,
                causer=changed_by,
                log="security",
            )
            record_security_event(
                SecurityEventType.ROLE_PERMISSIONS_CHANGED, user=changed_by, subject=role, properties=properties
            )
        authorization().flush()
        return role
