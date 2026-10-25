"""Generic OpenID Connect client (original ``OidcClient``, ADR 0007): authorization code flow
with PKCE (S256), state and nonce. Works with any standards compliant provider (Google
Workspace, Microsoft Entra ID, Keycloak, ...). The ID token is always verified locally:
signature (provider JWKS), issuer, audience, expiry and nonce.

allauth's ``openid_connect`` provider was not used for the flow: it skips the signature check
when the token came straight from the token endpoint and does not send or check a nonce, both
of which the original requires (see porting/phase-2-report.md). Accounts are linked in
``user_identities`` (``LinkIdentity``), not in allauth's ``socialaccount`` tables."""

from __future__ import annotations

import base64
import hashlib
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from django.core.cache import cache

from ninefruits.security.services.sso import OidcProvider

CACHE_SECONDS = 3600
LEEWAY_SECONDS = 60
TIMEOUT_SECONDS = 10.0


class OidcError(Exception):
    """The provider answered with something that cannot be trusted (original ``OidcException``)."""


def code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


class OidcClient:
    def __init__(self, http: httpx.Client | None = None) -> None:
        self._http = http

    def _client(self) -> httpx.Client:
        return self._http or httpx.Client(timeout=TIMEOUT_SECONDS)

    def _get_json(self, url: str) -> dict[str, Any]:
        client = self._client()
        try:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise OidcError(f"Could not read {url}.") from error
        finally:
            if self._http is None:
                client.close()
        if not isinstance(data, dict):
            raise OidcError(f"Unexpected answer from {url}.")
        return data

    def discovery(self, provider: OidcProvider) -> dict[str, Any]:
        key = f"oidc:{provider.key}:discovery"
        document = cache.get(key)
        if document is None:
            document = self._get_json(f"{provider.issuer}/.well-known/openid-configuration")
            for name in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
                if not isinstance(document.get(name), str):
                    raise OidcError(f"The OIDC discovery document of [{provider.key}] has no {name}.")
            cache.set(key, document, CACHE_SECONDS)
        return dict(document)

    def jwks(self, provider: OidcProvider) -> dict[str, Any]:
        key = f"oidc:{provider.key}:jwks"
        keys = cache.get(key)
        if keys is None:
            keys = self._get_json(self.discovery(provider)["jwks_uri"])
            cache.set(key, keys, CACHE_SECONDS)
        return dict(keys)

    def authorization_url(
        self, provider: OidcProvider, redirect_uri: str, state: str, nonce: str, code_verifier: str
    ) -> str:
        query = urlencode(
            {
                "response_type": "code",
                "client_id": provider.client_id,
                "redirect_uri": redirect_uri,
                "scope": " ".join(provider.scopes),
                "state": state,
                "nonce": nonce,
                "code_challenge": code_challenge(code_verifier),
                "code_challenge_method": "S256",
            }
        )
        return f"{self.discovery(provider)['authorization_endpoint']}?{query}"

    def exchange(
        self, provider: OidcProvider, code: str, redirect_uri: str, code_verifier: str, nonce: str
    ) -> dict[str, Any]:
        """Exchanges the code and returns the verified ID token claims."""
        client = self._client()
        try:
            response = client.post(
                self.discovery(provider)["token_endpoint"],
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": provider.client_id,
                    "client_secret": provider.client_secret,
                    "code_verifier": code_verifier,
                },
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise OidcError("The token request failed.") from error
        finally:
            if self._http is None:
                client.close()
        id_token = payload.get("id_token") if isinstance(payload, dict) else None
        if not isinstance(id_token, str):
            raise OidcError("The provider returned no ID token.")
        return self.verify(provider, id_token, nonce)

    def verify(self, provider: OidcProvider, id_token: str, nonce: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(id_token)
            key_set = jwt.PyJWKSet.from_dict(self.jwks(provider))
            kid = header.get("kid")
            candidates = [key for key in key_set.keys if kid is None or key.key_id == kid]
            if not candidates:
                raise OidcError("The ID token is signed with an unknown key.")
            claims = jwt.decode(
                id_token,
                key=candidates[0],
                algorithms=["RS256"],
                options={"verify_aud": False, "verify_iss": False, "require": ["exp", "iat"]},
                leeway=LEEWAY_SECONDS,
            )
        except OidcError:
            raise
        except jwt.PyJWTError as error:
            raise OidcError(f"The ID token is not valid: {error}") from error

        audience = claims.get("aud")
        audiences = [audience] if isinstance(audience, str) else list(audience or [])
        if str(claims.get("iss", "")).rstrip("/") != provider.issuer:
            raise OidcError("The ID token was issued by another provider.")
        if provider.client_id not in audiences:
            raise OidcError("The ID token is meant for another client.")
        if not isinstance(claims.get("nonce"), str) or not _equal(nonce, claims["nonce"]):
            raise OidcError("The ID token does not match this sign-in attempt.")
        if not isinstance(claims.get("sub"), str) or not claims["sub"]:
            raise OidcError("The ID token has no subject.")
        return claims


def _equal(left: str, right: str) -> bool:
    import hmac

    return hmac.compare_digest(left.encode(), right.encode())
