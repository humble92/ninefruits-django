""" "Remember this device" for two-factor authentication (original ``TrustedDevices``).

The cookie is signed (Django signing with the secret key) and bound to the user's current
two-factor enrollment: the authenticator app (row id and secret) and the email code
enrollment time. Resetting or re-enrolling therefore invalidates every remembered device. The
lifetime comes from ``SecuritySettings.mfa_remember_device_days``; 0 turns the feature off and
also ignores cookies issued before. allauth's own "trust this browser" stage is replaced by this
service (``MFA_TRUST_ENABLED = False``)."""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import TYPE_CHECKING, Any

from allauth.mfa.models import Authenticator
from django.conf import settings
from django.core import signing
from django.http import HttpRequest, HttpResponseBase

from .mfa_policy import MfaPolicy

if TYPE_CHECKING:
    from ninefruits.security.models import User

COOKIE = "mfa_trusted_device"
_SALT = "ninefruits.security.trusted_devices"


class TrustedDevices:
    def __init__(self, policy: MfaPolicy | None = None) -> None:
        self.policy = policy or MfaPolicy()

    def remember(self, response: HttpResponseBase, user: User) -> None:
        days = self.policy.remember_device_days()
        if days == 0:
            return
        expires_at = int(time.time()) + days * 86400
        value = signing.dumps(
            {"user_id": user.pk, "expires_at": expires_at, "signature": self.signature(user)}, salt=_SALT
        )
        response.set_cookie(
            COOKIE,
            value,
            max_age=days * 86400,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=True,
            samesite="Lax",
        )

    def is_trusted(self, request: HttpRequest, user: User) -> bool:
        days = self.policy.remember_device_days()
        if days == 0:
            return False
        payload = self._payload(request.COOKIES.get(COOKIE))
        if payload is None or payload.get("user_id") != user.pk:
            return False
        now = int(time.time())
        expires_at = payload.get("expires_at")
        if not isinstance(expires_at, int) or not now < expires_at <= now + days * 86400:
            return False
        signature = str(payload.get("signature", ""))
        # Cookies signed before a SECRET_KEY rotation stay valid while the old key is a fallback.
        keys = [settings.SECRET_KEY, *getattr(settings, "SECRET_KEY_FALLBACKS", [])]
        return any(hmac.compare_digest(self.signature(user, key), signature) for key in keys if key)

    def forget(self, response: HttpResponseBase) -> None:
        response.delete_cookie(COOKIE)

    @staticmethod
    def signature(user: User, secret_key: str | None = None) -> str:
        parts = [str(user.pk)]
        for authenticator in Authenticator.objects.filter(user_id=user.pk, type=Authenticator.Type.TOTP).order_by("pk"):
            parts.extend((str(authenticator.pk), str(authenticator.type), str(authenticator.data.get("secret", ""))))
        enabled = user.email_mfa_enabled_at
        parts.append(str(int(enabled.timestamp())) if enabled else "")
        key = hashlib.sha256(((secret_key or settings.SECRET_KEY) + _SALT).encode()).digest()
        return hmac.new(key, "|".join(parts).encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _payload(value: str | None) -> dict[str, Any] | None:
        if not value:
            return None
        try:
            data = signing.loads(value, salt=_SALT)
        except signing.BadSignature:
            return None
        return data if isinstance(data, dict) else None
