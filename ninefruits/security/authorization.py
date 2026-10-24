"""Authorization entry points used outside the security app (porting-plan 7.2)."""

from __future__ import annotations

from typing import Any

from ninefruits.security.enums import Permission


def can_access_admin(user: Any) -> bool:
    """Whether the user may open the admin panel (original ``canAccessPanel``): an active
    account holding ``admin_panel.access``."""
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and user.is_active
        and user.has_perm(Permission.ADMIN_PANEL_ACCESS)
    )
