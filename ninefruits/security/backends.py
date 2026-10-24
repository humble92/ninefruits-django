"""Authentication and authorization backends (porting-plan 7.1, 7.2)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.backends import BaseBackend


class CatalogPermissionBackend(BaseBackend):
    """Answers ``user.has_perm('resource.action', obj)`` from the permission catalog."""

    def has_perm(self, user_obj: Any, perm: str, obj: Any = None) -> bool:
        return False


class StudentNumberBackend(BaseBackend):
    """Sign-in with a student number instead of an email address."""

    def authenticate(self, request: Any, **credentials: Any) -> Any:
        return None
