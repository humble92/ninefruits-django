"""Request rates (porting-plan 12, ``DEFAULT_THROTTLE_RATES``):

- ``anon``: requests without a sign-in, per address (health, certificate verification);
- ``user``: signed-in users through the session, per account;
- ``integration``: integration tokens, per token (higher: platforms send whole rosters).

Each request is counted by exactly one of them."""

from __future__ import annotations

from typing import Any

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle

from .authentication import is_token_request


class AnonThrottle(AnonRateThrottle):
    scope = "anon"

    def get_ident(self, request: Any) -> str:
        """The client address as the other rate limits see it (``TRUSTED_PROXY_COUNT``)."""
        from ninefruits.core.http import client_ip

        return client_ip(request)


class UserThrottle(UserRateThrottle):
    scope = "user"

    def get_cache_key(self, request: Any, view: Any) -> str | None:
        if not request.user or not request.user.is_authenticated or is_token_request(request):
            return None
        return super().get_cache_key(request, view)


class IntegrationThrottle(SimpleRateThrottle):
    scope = "integration"

    def get_cache_key(self, request: Any, view: Any) -> str | None:
        if not is_token_request(request):
            return None
        return self.cache_format % {"scope": self.scope, "ident": request.auth.token_key}
