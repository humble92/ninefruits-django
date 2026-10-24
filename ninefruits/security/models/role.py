"""Roles and the permission catalog table (original ``App\\Models\\Security\\Role`` and
``Permission``, spatie/laravel-permission tables ``roles``, ``permissions``,
``role_has_permissions``). Only role/permission storage is used; users get roles through
``RoleAssignment`` (ADR 0005)."""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from ninefruits.core.models import VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.security.enums import Permission as PermissionName
from ninefruits.security.enums import Persona

#: The original's ``guard_name``; every row uses it.
GUARD_NAME = "web"


class Permission(models.Model):
    name = models.CharField(max_length=255)
    guard_name = models.CharField(max_length=255, default=GUARD_NAME)
    created_at = models.DateTimeField(null=True, blank=True, default=timezone.now, editable=False)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, editable=False)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "permissions"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "guard_name"], name="permissions_name_guard_name_unique"),
        ]

    def __str__(self) -> str:
        return self.label

    @property
    def label(self) -> str:
        try:
            return PermissionName(self.name).label
        except ValueError:
            return self.name


class RoleQuerySet(VisibleQuerySet):
    def assignable(self) -> RoleQuerySet:
        """Roles that can be assigned by hand (persona roles are granted from data)."""
        return self.filter(persona__isnull=True)


class Role(models.Model):
    name = models.CharField(max_length=255)
    guard_name = models.CharField(max_length=255, default=GUARD_NAME)
    display_name = TranslatableJSONField(max_length=None)
    description = TranslatableJSONField(null=True, blank=True, max_length=None)
    persona = models.CharField(max_length=255, null=True, blank=True, choices=Persona.choices)
    is_system = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True, blank=True, default=timezone.now, editable=False)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, editable=False)
    permissions = models.ManyToManyField(Permission, through="RoleHasPermission", related_name="roles", blank=True)

    objects = RoleQuerySet.as_manager()

    class Meta:
        db_table = "roles"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "guard_name"], name="roles_name_guard_name_unique"),
            models.UniqueConstraint(fields=["persona"], name="roles_persona_unique"),
        ]

    def __str__(self) -> str:
        return self.display_label

    @property
    def display_label(self) -> str:
        return str(self.display_name or self.name)

    def is_persona(self) -> bool:
        return self.persona is not None

    def permission_names(self) -> list[str]:
        return sorted(self.permissions.values_list("name", flat=True))

    def sync_permissions(self, names: list[str] | set[str]) -> None:
        """Replaces the role's permissions (spatie ``syncPermissions``). Unknown names are
        created like ``Permission::findOrCreate``."""
        wanted = set(names)
        existing = {p.name: p for p in Permission.objects.filter(name__in=wanted, guard_name=GUARD_NAME)}
        for missing in wanted - existing.keys():
            existing[missing] = Permission.objects.create(name=missing, guard_name=GUARD_NAME)
        RoleHasPermission.objects.filter(role=self).exclude(permission__in=existing.values()).delete()
        current = set(RoleHasPermission.objects.filter(role=self).values_list("permission_id", flat=True))
        RoleHasPermission.objects.bulk_create(
            [RoleHasPermission(role=self, permission=p) for p in existing.values() if p.pk not in current]
        )

    def give_permission_to(self, *names: str) -> None:
        self.sync_permissions({*self.permission_names(), *names})


class RoleHasPermission(models.Model):
    pk = models.CompositePrimaryKey("permission_id", "role_id")
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        db_table = "role_has_permissions"

    def __repr__(self) -> str:
        return f"<RoleHasPermission role={self.role_id} permission={self.permission_id}>"

    def __str__(self) -> str:
        return f"{self.role_id}:{self.permission_id}"
