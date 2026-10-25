"""Integration tokens (ADR 0004-django: knox). A token acts as its user: the same catalog
permissions, scopes and row level security. Only the SHA-512 digest is stored; the token text is
shown once when it is issued. Issuing and revoking are recorded in the business audit (log
``api``, events ``api.token_issued`` and ``api.token_revoked``) with the token's key prefix (the
first 15 characters, used for lookup, not enough to authenticate)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.translation import gettext as _
from knox.models import AuthToken

from ninefruits.audit.logger import audit
from ninefruits.security.enums import Permission

#: Longest lifetime of an issued token; tokens never live forever.
MAX_TOKEN_DAYS = 365
NOTE_MAX = 200


@dataclass(frozen=True)
class IssuedToken:
    token: str
    key: str
    expires_at: datetime | None


def token_rows(user: Any) -> list[dict[str, Any]]:
    """The user's tokens (never the token itself)."""
    return [
        {"key": token.token_key, "created_at": token.created, "expires_at": token.expiry}
        for token in AuthToken.objects.filter(user=user).order_by("-created")
    ]


class IssueApiToken:
    def __call__(
        self, user: Any, actor: Any = None, days: int | None = None, note: str | None = None, causer: Any = None
    ) -> IssuedToken:
        return self.handle(user, actor, days, note, causer)

    def handle(
        self, user: Any, actor: Any = None, days: int | None = None, note: str | None = None, causer: Any = None
    ) -> IssuedToken:
        """``actor`` issues for ``user``: the user themself (the API, signed in through the session)
        or an administrator with ``users.update`` for another account; ``None`` is the operator
        running the command (``causer``: the ``--actor`` named in the audit)."""
        if not user.is_active:
            raise ValidationError({"user": _("The account is not active.")})
        if actor is not None and actor.pk != user.pk and not actor.has_perm(Permission.USERS_UPDATE):
            raise PermissionDenied
        if days is not None and not 1 <= days <= MAX_TOKEN_DAYS:
            raise ValidationError(
                {"days": _("The lifetime must be between 1 and %(max)s days.") % {"max": MAX_TOKEN_DAYS}}
            )
        note = (note or "").strip()[:NOTE_MAX] or None
        with transaction.atomic():
            expiry = timedelta(days=days) if days is not None else None
            instance, token = AuthToken.objects.create(user, expiry) if expiry else AuthToken.objects.create(user)
            audit(
                "api.token_issued",
                user,
                reason=note,
                properties={"key_prefix": instance.token_key, "expires_at": _iso(instance.expiry)},
                causer=causer or actor,
                log="api",
            )
        return IssuedToken(token, instance.token_key, instance.expiry)


class RevokeApiTokens:
    def __call__(
        self, user: Any, actor: Any = None, key: str | None = None, reason: str | None = None, causer: Any = None
    ) -> int:
        return self.handle(user, actor, key, reason, causer)

    def handle(
        self, user: Any, actor: Any = None, key: str | None = None, reason: str | None = None, causer: Any = None
    ) -> int:
        """Revokes the user's token with the key prefix, or all of them. Returns how many."""
        if actor is not None and actor.pk != user.pk and not actor.has_perm(Permission.USERS_UPDATE):
            raise PermissionDenied
        tokens = AuthToken.objects.filter(user=user)
        if key:
            tokens = tokens.filter(token_key=key)
        with transaction.atomic():
            keys = list(tokens.values_list("token_key", flat=True))
            tokens.delete()
            if keys:
                audit(
                    "api.token_revoked",
                    user,
                    reason=(reason or "").strip()[:NOTE_MAX] or None,
                    properties={"key_prefixes": keys, "all": not key},
                    causer=causer or actor,
                    log="api",
                )
        return len(keys)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
