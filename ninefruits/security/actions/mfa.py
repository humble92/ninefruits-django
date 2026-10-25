"""Two-factor enrollment actions: authenticator app (original Fortify
``EnableTwoFactorAuthentication``, ``ConfirmTwoFactorAuthentication``,
``GenerateNewRecoveryCodes``), email codes (``EnableEmailMfa``), turning a method off
(``DisableMfaMethod``) and the administrator reset (``ResetUserMfa``).

TOTP secrets and recovery codes are allauth ``Authenticator`` rows (ADR 0001-django); the
secret is encrypted by ``MfaAdapter.encrypt``."""

from __future__ import annotations

from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret, validate_totp_code
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.security.enums import MfaMethod, MfaRequirement
from ninefruits.security.models import User
from ninefruits.security.services.email_code import PURPOSE_ENROLLMENT, EmailCodeChallenge
from ninefruits.security.services.mfa_policy import MfaPolicy


class StartAuthenticatorAppEnrollment:
    """First step: a new secret the user scans. It is kept by the caller (session) until the
    user confirms it with a code."""

    def __call__(self, user: User) -> str:
        secret: str = generate_totp_secret()
        record_security_event(SecurityEventType.MFA_ENABLED, user=user)
        return secret


class ConfirmAuthenticatorApp:
    """Second step: the code from the app proves the secret was stored. Creates the
    authenticator and, when missing, recovery codes. Returns the recovery codes."""

    def __call__(self, user: User, secret: str, code: str) -> list[str]:
        if not validate_totp_code(secret, code.strip()):
            raise ValidationError({"code": _("The provided two factor authentication code was invalid.")})
        with transaction.atomic():
            Authenticator.objects.filter(user_id=user.pk, type=Authenticator.Type.TOTP).delete()
            TOTP.activate(user, secret)
            codes: list[str] = RecoveryCodes.activate(user).generate_codes()
            record_security_event(SecurityEventType.MFA_CONFIRMED, user=user)
        return codes


class GenerateRecoveryCodes:
    def __call__(self, user: User) -> list[str]:
        if not Authenticator.objects.filter(user_id=user.pk, type=Authenticator.Type.TOTP).exists():
            raise ValidationError({"recovery_codes": _("Recovery codes need an authenticator app. Set one up first.")})
        with transaction.atomic():
            Authenticator.objects.filter(user_id=user.pk, type=Authenticator.Type.RECOVERY_CODES).delete()
            codes: list[str] = RecoveryCodes.activate(user).generate_codes()
            record_security_event(SecurityEventType.MFA_RECOVERY_CODES_REGENERATED, user=user)
        return codes


def recovery_codes_for(user: User) -> list[str]:
    """Unused recovery codes of the user (shown after confirming or regenerating)."""
    instance = Authenticator.objects.filter(user_id=user.pk, type=Authenticator.Type.RECOVERY_CODES).first()
    return RecoveryCodes(instance).get_unused_codes() if instance else []


class EnableEmailMfa:
    """Turns on email codes as a two-factor method after the user proves access to the account
    email with a code from ``EmailCodeChallenge`` (purpose: enrollment)."""

    def __init__(self, policy: MfaPolicy | None = None, email_codes: EmailCodeChallenge | None = None) -> None:
        self.policy = policy or MfaPolicy()
        self.email_codes = email_codes or EmailCodeChallenge()

    def __call__(self, user: User, code: str) -> None:
        if not self.policy.email_codes_allowed():
            raise ValidationError({"email_code": _("Email codes are not available at this institution.")})
        if not self.email_codes.verify(user, PURPOSE_ENROLLMENT, code):
            raise ValidationError({"email_code": _("The code is invalid or has expired.")})
        user.email_mfa_enabled_at = timezone.now().replace(microsecond=0)
        user.save(update_fields=["email_mfa_enabled_at", "updated_at"])
        record_security_event(SecurityEventType.MFA_EMAIL_ENABLED, user=user)


class DisableMfaMethod:
    """Turns off one two-factor method. When the policy requires two-factor authentication, the
    user must keep at least one other method."""

    def __init__(self, policy: MfaPolicy | None = None) -> None:
        self.policy = policy or MfaPolicy()

    def __call__(self, user: User, method: MfaMethod) -> None:
        remaining = [enrolled for enrolled in self.policy.methods_for(user) if enrolled != method]
        if not remaining and self.policy.requirement_for(user) == MfaRequirement.REQUIRED:
            raise ValidationError(
                {"disable": _("Two-factor authentication is required for your account and cannot be disabled.")}
            )
        if method == MfaMethod.AUTHENTICATOR_APP:
            with transaction.atomic():
                Authenticator.objects.filter(user_id=user.pk).delete()
                record_security_event(SecurityEventType.MFA_DISABLED, user=user)
        else:
            user.email_mfa_enabled_at = None
            user.save(update_fields=["email_mfa_enabled_at", "updated_at"])
            record_security_event(SecurityEventType.MFA_EMAIL_DISABLED, user=user)


class ResetUserMfa:
    """Administrator reset of a user's two-factor authentication, e.g. after a lost phone. A
    reason is required and the reset is audited. Remembered devices stop working because their
    signature includes the enrollment."""

    def __call__(self, user: User, reason: str, reset_by: User) -> None:
        with transaction.atomic():
            Authenticator.objects.filter(user_id=user.pk).delete()
            user.email_mfa_enabled_at = None
            user.mfa_grace_started_at = None
            user.save(update_fields=["email_mfa_enabled_at", "mfa_grace_started_at", "updated_at"])
            audit("mfa.reset", user, reason=reason, causer=reset_by, log="security")
            record_security_event(
                SecurityEventType.MFA_RESET, user=reset_by, subject=user, properties={"reason": reason}
            )
