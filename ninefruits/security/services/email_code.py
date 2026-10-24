"""One-time codes sent by email, for two-factor sign-in and for enrolling the email method
(original ``EmailCodeChallenge``).

Only a keyed hash of the code is stored (cache), it expires after ``CODE_LIFETIME_MINUTES``, is
single use, and is discarded after ``MAX_ATTEMPTS`` wrong entries. Sending is limited per user
(one per minute, ``SENDS_PER_HOUR`` per hour) so the feature cannot be used to flood a mailbox."""

from __future__ import annotations

import hashlib
import hmac
import math
import secrets
import time
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.cache import cache

from ninefruits.audit.security_events import SecurityEventType, record_security_event

if TYPE_CHECKING:
    from ninefruits.security.models import User

PURPOSE_LOGIN = "login"
PURPOSE_ENROLLMENT = "enrollment"


class EmailCodeChallenge:
    PURPOSE_LOGIN = PURPOSE_LOGIN
    PURPOSE_ENROLLMENT = PURPOSE_ENROLLMENT
    CODE_LIFETIME_MINUTES = 10
    MAX_ATTEMPTS = 5
    SENDS_PER_HOUR = 5
    RESEND_AFTER_SECONDS = 60

    def send(self, user: User, purpose: str) -> bool:
        """Sends a new code (replacing any earlier one). Returns False when rate limited."""
        minute_key = f"mfa-email-code-resend:{user.pk}"
        hour_key = f"mfa-email-code-hourly:{user.pk}"
        if _too_many(minute_key, 1) or _too_many(hour_key, self.SENDS_PER_HOUR):
            return False
        _hit(minute_key, self.RESEND_AFTER_SECONDS)
        _hit(hour_key, 3600)

        code = f"{secrets.randbelow(1_000_000):06d}"
        cache.set(
            self._key(user, purpose),
            {"hash": self._hash(user, purpose, code), "attempts": 0},
            self.CODE_LIFETIME_MINUTES * 60,
        )
        from ninefruits.security.notifications import send_two_factor_email_code

        send_two_factor_email_code(user, code, self.CODE_LIFETIME_MINUTES)
        record_security_event(SecurityEventType.MFA_EMAIL_CODE_SENT, user=user, properties={"purpose": purpose})
        return True

    def verify(self, user: User, purpose: str, code: str) -> bool:
        key = self._key(user, purpose)
        stored = cache.get(key)
        if not isinstance(stored, dict):
            return False
        if hmac.compare_digest(stored["hash"], self._hash(user, purpose, code.strip())):
            cache.delete(key)
            return True
        attempts = stored["attempts"] + 1
        if attempts >= self.MAX_ATTEMPTS:
            cache.delete(key)
        else:
            cache.set(key, {"hash": stored["hash"], "attempts": attempts}, self.CODE_LIFETIME_MINUTES * 60)
        return False

    def seconds_until_resend(self, user: User) -> int:
        entry = cache.get(f"mfa-email-code-resend:{user.pk}")
        if not isinstance(entry, dict):
            return 0
        return max(0, math.ceil(entry["reset_at"] - time.time()))

    @staticmethod
    def _key(user: User, purpose: str) -> str:
        return f"mfa-email-code:{purpose}:{user.pk}"

    @staticmethod
    def _hash(user: User, purpose: str, code: str) -> str:
        return hmac.new(
            settings.SECRET_KEY.encode(), f"{purpose}|{user.pk}|{code}".encode(), hashlib.sha256
        ).hexdigest()


def _too_many(key: str, limit: int) -> bool:
    entry = cache.get(key)
    return isinstance(entry, dict) and entry["reset_at"] > time.time() and entry["count"] >= limit


def _hit(key: str, decay_seconds: int) -> None:
    """Fixed window counter (Laravel ``RateLimiter::hit``): the window starts at the first hit."""
    now = time.time()
    entry = cache.get(key)
    if not isinstance(entry, dict) or entry["reset_at"] <= now:
        entry = {"count": 0, "reset_at": now + decay_seconds}
    entry["count"] += 1
    cache.set(key, entry, max(1, math.ceil(entry["reset_at"] - now)))
