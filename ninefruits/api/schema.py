"""OpenAPI extensions (drf-spectacular): the token authentication shows as the ``Token`` scheme."""

from __future__ import annotations

from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class TokenScheme(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    target_class = "ninefruits.api.authentication.TokenAuthentication"
    name = "tokenAuth"

    def get_security_definition(self, auto_schema: Any) -> dict[str, str]:
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": (
                'Integration token: "Token <token>" (issued with api_issue_token or POST /api/v1/auth/tokens/)'
            ),
        }
