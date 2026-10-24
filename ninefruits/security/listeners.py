"""Security log for authentication and two-factor events (original
``RecordAuthenticationEvents``, porting-plan 8). Connected in ``SecurityConfig.ready``."""

from __future__ import annotations

from typing import Any

from allauth.account import signals as account_signals
from allauth.mfa import signals as mfa_signals
from allauth.mfa.models import Authenticator
from django.contrib.auth import signals as auth_signals
from django.contrib.auth.models import update_last_login
from django.core.signals import request_started
from django.utils import timezone

from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.core import context
from ninefruits.core.db import session_context
from ninefruits.security.services.authorization import begin_scope


def handle_login(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    # The request context was set before sign-in; attribute the rest of the request (and the
    # users row update below) to the user.
    context.update(user_id=user.pk, actor=f"user:{user.pk}")
    session_context().for_user(user.pk, context.current().request_id)
    now = timezone.now().replace(microsecond=0)
    user.__class__._default_manager.filter(pk=user.pk).update(
        last_login=now, failed_login_count=0, locked_until=None, updated_at=now
    )
    user.last_login, user.failed_login_count, user.locked_until = now, 0, None
    record_security_event(SecurityEventType.LOGIN_SUCCEEDED, user=user, identifier=user.email)


def handle_failed(sender: Any, credentials: dict[str, Any], request: Any = None, **kwargs: Any) -> None:
    identifier = credentials.get("login") or credentials.get("email") or credentials.get("username")
    record_security_event(
        SecurityEventType.LOGIN_FAILED, identifier=str(identifier)[:255] if isinstance(identifier, str) else None
    )


def handle_logout(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    if user is not None:
        record_security_event(SecurityEventType.LOGOUT, user=user)


def handle_password_reset(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    record_security_event(SecurityEventType.PASSWORD_RESET, user=user)


def handle_email_confirmed(sender: Any, request: Any, email_address: Any, **kwargs: Any) -> None:
    """allauth verified the address: the original ``users.email_verified_at`` follows."""
    user = email_address.user
    if email_address.email.lower() == user.email.lower() and user.email_verified_at is None:
        user.email_verified_at = timezone.now().replace(microsecond=0)
        user.__class__._default_manager.filter(pk=user.pk).update(email_verified_at=user.email_verified_at)


def handle_mfa_failed(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    record_security_event(SecurityEventType.MFA_CHALLENGE_FAILED, user=user)


def handle_authenticator_used(sender: Any, request: Any, user: Any, authenticator: Any, **kwargs: Any) -> None:
    if authenticator.type == Authenticator.Type.RECOVERY_CODES:
        record_security_event(SecurityEventType.MFA_RECOVERY_CODE_USED, user=user)


def connect() -> None:
    # last_login is written by handle_login after the database context names the user.
    auth_signals.user_logged_in.disconnect(update_last_login, dispatch_uid="update_last_login")
    auth_signals.user_logged_in.connect(handle_login, dispatch_uid="ninefruits.security.login")
    auth_signals.user_login_failed.connect(handle_failed, dispatch_uid="ninefruits.security.login_failed")
    auth_signals.user_logged_out.connect(handle_logout, dispatch_uid="ninefruits.security.logout")
    account_signals.password_reset.connect(handle_password_reset, dispatch_uid="ninefruits.security.password_reset")
    account_signals.email_confirmed.connect(handle_email_confirmed, dispatch_uid="ninefruits.security.email_confirmed")
    mfa_signals.authentication_failed.connect(handle_mfa_failed, dispatch_uid="ninefruits.security.mfa_failed")
    mfa_signals.authenticator_used.connect(handle_authenticator_used, dispatch_uid="ninefruits.security.mfa_used")
    # Scoped authorization: a new AuthorizationService/PersonaResolver per request and task.
    request_started.connect(begin_scope, dispatch_uid="ninefruits.security.begin_scope")
    try:
        from celery.signals import task_prerun
    except ImportError:  # pragma: no cover
        return
    task_prerun.connect(begin_scope, dispatch_uid="ninefruits.security.begin_scope_task", weak=False)
