"""Health, certificate verification and the current user (porting-plan 12).

- ``GET /api/v1/health/``: for load balancers and monitoring, no sign-in. ``ok`` (200) when the
  database and the cache answer, ``degraded`` (200) when the scheduler heartbeat is stale,
  ``unavailable`` (503) otherwise. Users with ``admin_panel.access`` also get each check.
- ``GET /api/v1/certificates/verify/<code>/``: the certificate verification JSON
  (``VerificationResult.as_dict()``: only what the paper shows), no sign-in, 30 requests a minute
  per address like the public page.
- ``GET /api/v1/me/``: who the session or token is, and their catalog permissions."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ninefruits.security.enums import Permission

HEARTBEAT_STALE_AFTER = timedelta(minutes=5)


def _check_database() -> str:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return "failed"
    return "ok"


def _check_cache() -> str:
    key = "api:health"
    try:
        cache.set(key, "1", 30)
        return "ok" if cache.get(key) == "1" else "failed"
    except Exception:
        return "failed"


def _check_heartbeat() -> str:
    from ninefruits.core.tasks import HEARTBEAT_CACHE_KEY

    try:
        value = cache.get(HEARTBEAT_CACHE_KEY)
    except Exception:
        return "failed"
    if not value:
        return "stale"
    try:
        beat = datetime.fromisoformat(str(value))
    except ValueError:
        return "stale"
    return "ok" if timezone.now() - beat <= HEARTBEAT_STALE_AFTER else "stale"


class HealthView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request: Request) -> Response:
        checks = {"database": _check_database(), "cache": _check_cache(), "scheduler": _check_heartbeat()}
        if checks["database"] != "ok" or checks["cache"] != "ok":
            state, code = "unavailable", 503
        elif checks["scheduler"] != "ok":
            state, code = "degraded", 200
        else:
            state, code = "ok", 200
        body: dict[str, Any] = {"status": state}
        user = request.user
        if user is not None and user.is_authenticated and user.has_perm(Permission.ADMIN_PANEL_ACCESS):
            body["checks"] = checks
        return Response(body, status=code, headers={"Cache-Control": "no-store"})


class CertificateVerificationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request: Request, code: str) -> Response:
        from ninefruits.certificate.services.verification import CertificateVerification

        result = CertificateVerification().check(code)
        return Response(result.as_dict(), headers={"X-Robots-Tag": "noindex", "Cache-Control": "no-store"})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request: Request) -> Response:
        from .tokens import token_auth

        user = request.user
        if not user.is_authenticated:  # IsAuthenticated lets only signed-in users through
            raise NotAuthenticated
        token = token_auth(request)
        return Response(
            {
                "id": user.pk,
                "email": user.email,
                "permissions": sorted(str(p) for p in Permission if user.has_perm(p)),
                "authentication": "token" if token is not None else "session",
                "token": None if token is None else {"key": token.token_key, "expires_at": token.expiry},
            }
        )
