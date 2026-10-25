"""Integration tokens of the signed-in user (ADR 0004-django).

- ``GET /api/v1/auth/tokens/``: the user's tokens (key prefix, created, expiry);
- ``POST /api/v1/auth/tokens/``: issues a token (``{"days": 90, "note": "..."}``). Only through the
  browser session, never with another token, so a token always follows a full sign-in with the
  two-factor policy. The token text is in the response once;
- ``DELETE /api/v1/auth/tokens/current/``: revokes the token of this request;
- ``DELETE /api/v1/auth/tokens/<key>/``: revokes one of the user's tokens.

Administrators issue tokens for service accounts with ``api_issue_token``. Issuing and revoking
are audited (``api.token_issued``, ``api.token_revoked``)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ninefruits.api.actions import IssueApiToken, RevokeApiTokens, token_rows
from ninefruits.api.permissions import SessionOnly
from ninefruits.api.serializers import TokenRequestSerializer


def token_auth(request: Any) -> Any:
    from ninefruits.api.authentication import is_token_request

    return request.auth if is_token_request(request) else None


class TokenListView(APIView):
    def get_permissions(self) -> list[Any]:
        return [SessionOnly()] if self.request.method == "POST" else [IsAuthenticated()]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request: Request) -> Response:
        return Response({"tokens": token_rows(request.user)})

    @extend_schema(request=TokenRequestSerializer, responses={201: OpenApiTypes.OBJECT})
    def post(self, request: Request) -> Response:
        data = TokenRequestSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            issued = IssueApiToken()(
                request.user, request.user, data.validated_data.get("days"), data.validated_data.get("note")
            )
        except DjangoValidationError as error:
            raise ValidationError(error.message_dict if hasattr(error, "error_dict") else error.messages) from error
        return Response(
            {"token": issued.token, "key": issued.key, "expires_at": issued.expires_at},
            status=status.HTTP_201_CREATED,
            headers={"Cache-Control": "no-store"},
        )


class TokenDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={204: None})
    def delete(self, request: Request, key: str) -> Response:
        if key == "current":
            token = token_auth(request)
            if token is None:
                raise ValidationError({"detail": "This request is not authenticated with a token."})
            key = token.token_key
        if RevokeApiTokens()(request.user, request.user, key) == 0:
            raise NotFound
        return Response(status=status.HTTP_204_NO_CONTENT)
