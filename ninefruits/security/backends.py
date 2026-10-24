"""Authentication and authorization backends (porting-plan 7.1, 7.2)."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import make_password
from django.http import HttpRequest

from ninefruits.security.enums import Permission

_CATALOG = frozenset(permission.value for permission in Permission)


class CatalogPermissionBackend(BaseBackend):
    """Answers ``user.has_perm(...)``. Catalog permission names (``users.view``) come from role
    assignments and personas (original ``Gate::before``); other abilities, and catalog names
    the user does not hold when a record is given, go to the record's policy."""

    def has_perm(self, user_obj: Any, perm: str, obj: Any = None) -> bool:
        if user_obj is None or not getattr(user_obj, "is_authenticated", False) or not user_obj.is_active:
            return False
        perm = str(perm)
        if perm in _CATALOG:
            from ninefruits.security.services.authorization import authorization

            if authorization().has_permission(user_obj, perm):
                return True
        if obj is None:
            return False
        from ninefruits.security.policies import policy_for

        policy = policy_for(obj)
        return policy is not None and policy.allows(user_obj, perm, obj)

    def get_user(self, user_id: Any) -> Any:
        from ninefruits.security.models import User

        return User.objects.filter(pk=user_id).first()


class LoginIdentifierBackend(BaseBackend):
    """Password sign-in with the email or a student number (original
    ``Fortify::authenticateUsing``). Deactivated, locked and SSO-only accounts get the same
    failure as a wrong password; a wrong password counts towards the account lockout."""

    def authenticate(self, request: HttpRequest | None, **credentials: Any) -> Any:
        password = credentials.get("password")
        identifier = credentials.get("login") or credentials.get("email") or credentials.get("username")
        if not password or not identifier:
            return None
        from ninefruits.security.models import UserIdentity
        from ninefruits.security.services.lockout import AccountLockout
        from ninefruits.security.services.login_identifier import LoginIdentifierResolver
        from ninefruits.settings.groups.authentication import AuthenticationSettings

        settings = AuthenticationSettings.load()
        user = LoginIdentifierResolver(settings).resolve(str(identifier))
        if user is None or not user.is_active or user.is_locked():
            make_password(password)  # same work as a real check, so timing reveals nothing
            return None
        if not user.check_password(password):
            AccountLockout(settings).record_failure(user)
            return None
        if not settings.password_login_for_sso_users and UserIdentity.objects.filter(user=user).exists():
            return None
        return user

    def get_user(self, user_id: Any) -> Any:
        from ninefruits.security.models import User

        return User.objects.filter(pk=user_id).first()


#: Student numbers are resolved by ``LoginIdentifierBackend`` (kept for the settings name).
StudentNumberBackend = LoginIdentifierBackend
