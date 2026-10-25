"""School sign-in providers (original ``OidcProvider`` and the provider list of ``OidcClient``).

Providers are configured in ``AuthenticationSettings.sso_providers`` (client secrets encrypted
with ``ninefruits.security.crypto``). Links between accounts and provider subjects live in
``user_identities`` (``LinkIdentity``/``UnlinkIdentity``). The sign-in flow (authorization
code + PKCE, state, nonce, local ID token verification, linking by institutional email, the
``trusts_mfa`` rule) is ``ninefruits.security.services.oidc`` and ``ninefruits.security.views_sso``."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ninefruits.security.crypto import decrypt_string


@dataclass(frozen=True, slots=True)
class OidcProvider:
    key: str
    label: str
    issuer: str
    client_id: str
    client_secret: str
    scopes: tuple[str, ...] = field(default=("openid", "email", "profile"))
    trusts_mfa: bool = False
    is_enabled: bool = True

    @classmethod
    def from_settings(cls, config: dict[str, Any]) -> OidcProvider:
        secret = str(config.get("client_secret") or "")
        scopes = [scope for scope in re.split(r"[\s,]+", str(config.get("scopes") or "openid email profile")) if scope]
        return cls(
            key=str(config["key"]),
            label=str(config.get("label") or config["key"]),
            issuer=str(config.get("issuer", "")).rstrip("/"),
            client_id=str(config.get("client_id", "")),
            client_secret=decrypt_string(secret) if secret else "",
            scopes=tuple(scopes),
            trusts_mfa=bool(config.get("trusts_mfa", False)),
            is_enabled=bool(config.get("is_enabled", True)),
        )

    def __repr__(self) -> str:
        return f"<OidcProvider {self.key}>"


def enabled_providers() -> list[OidcProvider]:
    from ninefruits.settings.groups.authentication import AuthenticationSettings

    providers = [OidcProvider.from_settings(config) for config in AuthenticationSettings.load().sso_providers]
    return [provider for provider in providers if provider.is_enabled]


def provider(key: str) -> OidcProvider | None:
    return next((candidate for candidate in enabled_providers() if candidate.key == key), None)
