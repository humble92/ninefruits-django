"""Catalog permissions for API views (porting-plan 12)::

    permission_classes = [HasCatalogPermission(Permission.LMS_MANAGE)]

The user must be signed in (session or token) and hold every given catalog permission
(``user.has_perm``, the same answer as the admin and portal)."""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import BasePermission

from ninefruits.security.enums import Permission


class HasCatalogPermission(BasePermission):
    def __init__(self, *permissions: Permission | str) -> None:
        if not permissions:
            raise ValueError("Name at least one catalog permission.")
        self.permissions = tuple(str(permission) for permission in permissions)

    def __call__(self) -> HasCatalogPermission:
        """DRF instantiates each entry of ``permission_classes``; an instance stands for itself."""
        return self

    def __repr__(self) -> str:
        return f"HasCatalogPermission({', '.join(self.permissions)})"

    def has_permission(self, request: Any, view: Any) -> bool:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        return all(user.has_perm(permission) for permission in self.permissions)


class SessionOnly(BasePermission):
    """Signed in through the browser session (not with a token): issuing tokens needs a full
    sign-in with the two-factor policy, never another token."""

    def has_permission(self, request: Any, view: Any) -> bool:
        from .authentication import is_token_request

        user = getattr(request, "user", None)
        return bool(user is not None and user.is_authenticated and not is_token_request(request))
