from __future__ import annotations

from typing import TypedDict

from django.db import transaction

from ninefruits.security.enums import Permission as PermissionName
from ninefruits.security.models import GUARD_NAME, Permission, Role
from ninefruits.security.services.authorization import authorization


class SyncPlan(TypedDict):
    created: list[str]
    deleted: list[str]


class SyncPermissionCatalog:
    """Makes the permissions table match the catalog enum and gives system roles every
    permission."""

    def plan(self) -> SyncPlan:
        """What ``__call__`` would change, without changing anything."""
        catalog = [permission.value for permission in PermissionName]
        existing = list(Permission.objects.filter(guard_name=GUARD_NAME).values_list("name", flat=True))
        return {
            "created": [name for name in catalog if name not in existing],
            "deleted": [name for name in existing if name not in catalog],
        }

    def __call__(self) -> SyncPlan:
        plan = self.plan()
        with transaction.atomic():
            Permission.objects.bulk_create([Permission(name=name, guard_name=GUARD_NAME) for name in plan["created"]])
            Permission.objects.filter(guard_name=GUARD_NAME, name__in=plan["deleted"]).delete()
            every = list(Permission.objects.filter(guard_name=GUARD_NAME).values_list("name", flat=True))
            for role in Role.objects.filter(is_system=True):
                role.sync_permissions(every)
        authorization().flush()
        return plan
