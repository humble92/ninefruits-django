"""Account actions: staff edits (``UpdateUserAccount``), unlocking (``UnlockUser``), and the
user's own password and profile changes (original Fortify ``UpdateUserPassword``,
``ResetUserPassword``, ``UpdateUserProfileInformation``)."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.security.models import User
from ninefruits.security.services.authorization import authorization


def end_sessions(user: User, keep_session_key: str | None = None) -> int:
    """Ends the user's sessions except ``keep_session_key`` (the original deleted the rows of its
    ``sessions`` table; Django sessions are found by their signed-in user id). Returns how many
    were ended."""
    engine = import_module(settings.SESSION_ENGINE)
    ended = 0
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if session.session_key == keep_session_key:
            continue
        if str(session.get_decoded().get("_auth_user_id")) == str(user.pk):
            # SessionStore.delete() also clears the cache of cached session engines.
            engine.SessionStore(session_key=session.session_key).delete()
            ended += 1
    return ended


def unverify_email(user: User) -> None:
    """A new address must be verified again (allauth keeps its own verification rows)."""
    from allauth.account.models import EmailAddress

    user.email_verified_at = None
    EmailAddress.objects.filter(user=user).delete()


class UpdateUserAccount:
    """Staff edit of an account (name, email, locale, active flag). Changing the email resets
    verification, ends the account's sessions and leaves a security event; nobody edits an
    account more privileged than their own or deactivates themselves (security review H4)."""

    EDITABLE = ("name", "email", "locale", "is_active")

    def __call__(self, user: User, data: dict[str, Any], actor: User) -> User:
        self._guard(user, data, actor)
        with transaction.atomic():
            previous_email = user.email
            for name in self.EDITABLE:
                if name in data:
                    value = data[name]
                    setattr(user, name, value.lower() if name == "email" and isinstance(value, str) else value)
            email_changed = user.email != previous_email
            if email_changed:
                unverify_email(user)
            user.save()
            if email_changed:
                end_sessions(user)
                record_security_event(
                    SecurityEventType.EMAIL_CHANGED,
                    user=user,
                    identifier=previous_email,
                    subject=user,
                    properties={"to": user.email, "by": actor.pk},
                )
                audit(
                    "user.email_changed",
                    user,
                    properties={"from": previous_email, "to": user.email},
                    causer=actor,
                    log="security",
                )
        authorization().flush()
        return user

    @staticmethod
    def _guard(user: User, data: dict[str, Any], actor: User) -> None:
        if actor.pk == user.pk and "is_active" in data and not data["is_active"]:
            raise ValidationError({"is_active": _("You cannot deactivate your own account.")})
        if actor.pk == user.pk:
            return
        service = authorization()
        held = set(service.permission_names(actor))
        missing = [name for name in service.permission_names(user) if name not in held]
        if missing:
            raise ValidationError(
                {
                    "email": _(
                        "This account holds permissions you do not have (%(permissions)s); only an "
                        "administrator with those permissions can change it."
                    )
                    % {"permissions": ", ".join(missing[:3])}
                }
            )


class UnlockUser:
    """Administrator release of an account locked after failed passwords, before the lock ends
    by itself. A reason is required."""

    def __call__(self, user: User, reason: str, unlocked_by: User | None) -> None:
        with transaction.atomic():
            user.failed_login_count = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_count", "locked_until", "updated_at"])
            audit("account.unlocked", user, reason=reason, causer=unlocked_by, log="security")
            record_security_event(
                SecurityEventType.ACCOUNT_UNLOCKED, user=unlocked_by, subject=user, properties={"reason": reason}
            )


class UpdateUserPassword:
    """The user changes their own password. Other sessions stop working (security review M7)
    and a security event is recorded. ``current_session_key`` is the session to keep."""

    def __call__(
        self,
        user: User,
        current_password: str,
        password: str,
        password_confirmation: str,
        current_session_key: str | None = None,
    ) -> None:
        errors: dict[str, list[str]] = {}
        if not user.check_password(current_password):
            errors["current_password"] = [_("The provided password does not match your current password.")]
        if password != password_confirmation:
            errors["password"] = [_("The password field confirmation does not match.")]
        else:
            try:
                validate_password(password, user)
            except ValidationError as error:
                errors["password"] = list(error.messages)
        if errors:
            raise ValidationError(errors)
        with transaction.atomic():
            user.set_password(password)
            user.remember_token = get_random_string(60)
            user.save(update_fields=["password", "remember_token", "updated_at"])
            end_sessions(user, keep_session_key=current_session_key)
            record_security_event(SecurityEventType.PASSWORD_CHANGED, user=user)


class ResetUserPassword:
    """A forgotten password is replaced through the reset link (allauth flow)."""

    def __call__(self, user: User, password: str) -> None:
        validate_password(password, user)
        user.set_password(password)
        user.save(update_fields=["password", "updated_at"])


class UpdateUserProfileInformation:
    """The user's own name and email. A new email address must be verified again and other
    sessions end (porting-plan 7.1, security review M7)."""

    def __call__(self, user: User, name: str, email: str, current_session_key: str | None = None) -> None:
        email = email.strip().lower()
        if User.objects.filter(email=email).exclude(pk=user.pk).exists():
            raise ValidationError({"email": _("The email has already been taken.")})
        with transaction.atomic():
            email_changed = email != user.email
            previous_email = user.email
            user.name = name
            user.email = email
            if email_changed:
                unverify_email(user)
            user.save()
            if email_changed:
                end_sessions(user, keep_session_key=current_session_key)
                record_security_event(
                    SecurityEventType.EMAIL_CHANGED, user=user, identifier=previous_email, properties={"to": email}
                )
