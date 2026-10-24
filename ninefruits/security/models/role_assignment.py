"""Role assignments (original ``App\\Models\\Security\\RoleAssignment``): a role granted to a
user within a scope (global, org unit, program) for a period. Assignments are never edited;
they are ended and new ones are created, so the history stays readable."""

from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.db import connection, models
from django.utils import timezone

from ninefruits.core.models import VisibleQuerySet
from ninefruits.security.enums import ScopeType

from .role import Role


class RoleAssignmentQuerySet(VisibleQuerySet):
    def active(self, at: datetime | None = None) -> RoleAssignmentQuerySet:
        """Assignments in effect at the given time (default now)."""
        at = at or timezone.now()
        return self.filter(models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=at)).filter(
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=at)
        )


class RoleAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="role_assignments")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="assignments")
    scope_type = models.CharField(max_length=32, choices=ScopeType.choices, default=ScopeType.GLOBAL)
    scope_id = models.BigIntegerField(null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(null=True, blank=True, default=timezone.now, editable=False)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, editable=False)

    objects = RoleAssignmentQuerySet.as_manager()

    class Meta:
        db_table = "role_assignments"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.role} ({self.describe_scope()})"

    def __repr__(self) -> str:
        return f"<RoleAssignment {self.pk} user={self.user_id} role={self.role_id}>"

    @property
    def scope(self) -> ScopeType:
        return ScopeType(self.scope_type)

    def is_active(self, at: datetime | None = None) -> bool:
        at = at or timezone.now()
        return (self.starts_at is None or self.starts_at <= at) and (self.ends_at is None or self.ends_at > at)

    def describe_scope(self) -> str:
        """ "All", or the scope type with the org unit / program code and name."""
        if self.scope == ScopeType.GLOBAL:
            return self.scope.label
        table_lookup = {
            ScopeType.ORG_UNIT: "SELECT code, util.i18n(name) FROM org_units WHERE id = %s",
            ScopeType.PROGRAM: "SELECT code, util.i18n(name) FROM programs WHERE id = %s",
        }
        # Org units and programs get models in Phase 1; until then read the two columns.
        with connection.cursor() as cursor:
            cursor.execute(table_lookup[self.scope], [self.scope_id])
            row = cursor.fetchone()
        target = f"#{self.scope_id}" if row is None else f"{row[0]} {row[1] or ''}".strip()
        return f"{self.scope.label}: {target}"
