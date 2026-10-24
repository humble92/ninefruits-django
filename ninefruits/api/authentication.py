"""API authentication (ADR 0004-django): the session (portal and admin pages) and knox tokens
(integrations).

DRF authenticates inside the view, after ``SetDatabaseSessionContextMiddleware`` has run for an
anonymous request, so a token request passes its user to PostgreSQL here: row level security,
the data audit triggers and the business audit see the token's user, as for a signed-in user.
The middleware resets the context when the request ends."""

from __future__ import annotations

from typing import Any

from knox.auth import TokenAuthentication as KnoxTokenAuthentication

from ninefruits.core import context
from ninefruits.core.db import session_context


class TokenAuthentication(KnoxTokenAuthentication):
    """``Authorization: Token <token>``. Inactive accounts are refused (knox)."""

    def authenticate(self, request: Any) -> tuple[Any, Any] | None:
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        context.update(user_id=user.pk, actor=f"user:{user.pk}")
        session_context().for_user(user.pk, context.current().request_id)
        return user, token


def is_token_request(request: Any) -> bool:
    """Whether the request was authenticated with an integration token."""
    from knox.models import AuthToken

    return isinstance(getattr(request, "auth", None), AuthToken)
