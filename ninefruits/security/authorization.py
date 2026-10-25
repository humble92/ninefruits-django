"""Authorization entry points used outside the security app (porting-plan 7.2)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest

from ninefruits.security.enums import Permission

if TYPE_CHECKING:
    from ninefruits.security.models import User


def can_access_admin(user: Any) -> bool:
    """Whether the user may open the admin panel (original ``canAccessPanel``): an active
    account holding ``admin_panel.access``."""
    return bool(
        user is not None
        and getattr(user, "is_authenticated", False)
        and user.is_active
        and user.has_perm(Permission.ADMIN_PANEL_ACCESS)
    )


def policy_allows(user: Any, ability: str, target: Any) -> bool:
    """A model policy ability (``view_any``, ``create``, ``resync`` ...) for an instance or a
    model class, like the original ``Gate::allows('create', Model::class)``. The permission
    backend accepts any object as ``obj`` (Django passes it through); this is the typed entry
    point for model classes, which django-stubs does not allow in ``has_perm``."""
    return bool(user.has_perm(ability, target))


def signed_in_user(request: HttpRequest) -> User:
    """The signed-in user of a view that requires sign-in (``LoginRequiredMixin``). An anonymous
    request raises ``PermissionDenied``, so a view wired without the sign-in check fails closed."""
    user = request.user
    if not user.is_authenticated:
        raise PermissionDenied
    return user
