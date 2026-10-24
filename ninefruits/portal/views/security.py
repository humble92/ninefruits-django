"""Portal security page ``/portal/security/`` (original ``App\\Livewire\\Portal\\SecuritySettings``).

Two-factor enrollment (authenticator app with recovery codes, email codes), this device's
"remember me" for two-factor, the password, and school sign-in (SSO) links, shared by every user
type. The admin panel links here, so a user enrolls once for both the portal and the admin
panel (ADR 0001). Changing two-factor settings or SSO links needs a recent password
confirmation (allauth reauthentication, three hours like the original ``password_timeout``).

One Livewire component -> one view: GET renders the page, POST runs ``action`` and renders the
page again (or, for HTMX requests, the changed section as a template partial)."""

from __future__ import annotations

from typing import Any

from allauth.account.internal.flows.reauthentication import did_recently_reauthenticate
from allauth.mfa.adapter import get_adapter as get_mfa_adapter
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import NoReverseMatch, reverse
from django.utils.http import urlencode
from django.utils.translation import gettext as _
from django.views import View

from ninefruits.security.actions import (
    ConfirmAuthenticatorApp,
    DisableMfaMethod,
    EnableEmailMfa,
    GenerateRecoveryCodes,
    StartAuthenticatorAppEnrollment,
    UnlinkIdentity,
    UpdateUserPassword,
)
from ninefruits.security.enums import MfaMethod, MfaRequirement
from ninefruits.security.models import UserIdentity
from ninefruits.security.services.email_code import PURPOSE_ENROLLMENT, EmailCodeChallenge
from ninefruits.security.services.mfa_policy import MfaPolicy
from ninefruits.security.services.sso import enabled_providers
from ninefruits.security.services.trusted_devices import TrustedDevices

TEMPLATE = "portal/security.html"
PENDING_SECRET_KEY = "security.totp.pending_secret"  # noqa: S105 - session key name
EMAIL_CODE_SENT_KEY = "security.email_code_sent"

#: Actions and the section partial an HTMX request gets back.
ACTIONS: dict[str, str] = {
    "enable": "authenticator",
    "confirm": "authenticator",
    "regenerate_recovery_codes": "authenticator",
    "disable": "authenticator",
    "send_email_code": "email",
    "confirm_email": "email",
    "disable_email": "email",
    "forget_device": "device",
    "unlink_identity": "sso",
    "change_password": "password",
}
#: Actions that change nothing until the password was confirmed recently.
NEEDS_CONFIRMATION = frozenset(ACTIONS) - {"change_password", "forget_device"}


class SecurityView(LoginRequiredMixin, View):
    def get(self, request: HttpRequest) -> HttpResponse:
        # A sent enrollment code belongs to the page the user was on (Livewire state).
        request.session.pop(EMAIL_CODE_SENT_KEY, None)
        return self.render_page(request)

    def post(self, request: HttpRequest) -> HttpResponse:
        action = request.POST.get("action", "")
        if action not in ACTIONS:
            return HttpResponseBadRequest()
        if action in NEEDS_CONFIRMATION and not did_recently_reauthenticate(request):
            return self.require_password_confirmation(request)
        extra: dict[str, Any] = {"section": ACTIONS[action]}
        errors: dict[str, list[str]] = {}
        try:
            response = getattr(self, f"do_{action}")(request, extra)
        except ValidationError as error:
            errors = error.message_dict if hasattr(error, "error_dict") else {"__all__": error.messages}
            response = None
        if isinstance(response, HttpResponse):
            return response
        partial = ACTIONS[action] if request.headers.get("HX-Request") else None
        page = self.render_page(request, errors=errors, partial=partial, **extra)
        if action == "forget_device":
            TrustedDevices().forget(page)
        return page

    # -- actions (original component methods) ----------------------------------------------
    def do_enable(self, request: HttpRequest, extra: dict[str, Any]) -> None:
        request.session[PENDING_SECRET_KEY] = StartAuthenticatorAppEnrollment()(request.user)  # type: ignore[arg-type]

    def do_confirm(self, request: HttpRequest, extra: dict[str, Any]) -> None:
        secret = request.session.get(PENDING_SECRET_KEY)
        code = request.POST.get("code", "").strip()
        if not secret:
            raise ValidationError({"code": _("Start the setup again.")})
        if not (len(code) == 6 and code.isdigit()):
            raise ValidationError({"code": _("The code must be 6 digits.")})
        extra["recovery_codes"] = ConfirmAuthenticatorApp()(request.user, secret, code)  # type: ignore[arg-type]
        request.session.pop(PENDING_SECRET_KEY, None)

    def do_regenerate_recovery_codes(self, request: HttpRequest, extra: dict[str, Any]) -> None:
        extra["recovery_codes"] = GenerateRecoveryCodes()(request.user)  # type: ignore[arg-type]

    def do_disable(self, request: HttpRequest, extra: dict[str, Any]) -> None:
        DisableMfaMethod()(request.user, MfaMethod.AUTHENTICATOR_APP)  # type: ignore[arg-type]
        request.session.pop(PENDING_SECRET_KEY, None)

    def do_send_email_code(self, request: HttpRequest, extra: dict[str, Any]) -> None:
        if not MfaPolicy().email_codes_allowed():
            raise ValidationError({"email_code": _("Email codes are not available at this institution.")})
        challenge = EmailCodeChallenge()
        if not challenge.send(request.user, PURPOSE_ENROLLMENT):  # type: ignore[arg-type]
            raise ValidationError(
                {
                    "email_code": _("Please wait %(seconds)s seconds before requesting another code.")
                    % {"seconds": challenge.seconds_until_resend(request.user)}  # type: ignore[arg-type]
                }
            )
        request.session[EMAIL_CODE_SENT_KEY] = True

    def do_confirm_email(self, request: HttpRequest, extra: dict[str, Any]) -> None:
        code = request.POST.get("email_code", "").strip()
        if not (len(code) == 6 and code.isdigit()):
            raise ValidationError({"email_code": _("The email code must be 6 digits.")})
        EnableEmailMfa()(request.user, code)  # type: ignore[arg-type]
        request.session.pop(EMAIL_CODE_SENT_KEY, None)

    def do_disable_email(self, request: HttpRequest, extra: dict[str, Any]) -> None:
        DisableMfaMethod()(request.user, MfaMethod.EMAIL_CODE)  # type: ignore[arg-type]

    def do_forget_device(self, request: HttpRequest, extra: dict[str, Any]) -> None:
        extra["device_forgotten"] = True

    def do_unlink_identity(self, request: HttpRequest, extra: dict[str, Any]) -> None:
        identity = get_object_or_404(UserIdentity, pk=request.POST.get("identity_id"), user=request.user)
        UnlinkIdentity()(request.user, identity)  # type: ignore[arg-type]

    def do_change_password(self, request: HttpRequest, extra: dict[str, Any]) -> None:
        UpdateUserPassword()(
            request.user,  # type: ignore[arg-type]
            request.POST.get("current_password", ""),
            request.POST.get("password", ""),
            request.POST.get("password_confirmation", ""),
            current_session_key=request.session.session_key,
        )
        update_session_auth_hash(request, request.user)  # type: ignore[arg-type]
        extra["password_changed"] = True

    # -- rendering ---------------------------------------------------------------------------
    def require_password_confirmation(self, request: HttpRequest) -> HttpResponse:
        """Sends the user to the password confirmation and back here afterwards."""
        url = f"{reverse('account_reauthenticate')}?{urlencode({'next': reverse('portal:security')})}"
        if request.headers.get("HX-Request"):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = url
            return response
        return HttpResponseRedirect(url)

    def render_page(
        self,
        request: HttpRequest,
        *,
        errors: dict[str, list[str]] | None = None,
        partial: str | None = None,
        **extra: Any,
    ) -> HttpResponse:
        user = request.user
        policy = MfaPolicy()
        methods = policy.methods_for(user)  # type: ignore[arg-type]
        secret = request.session.get(PENDING_SECRET_KEY)
        uses_app = MfaMethod.AUTHENTICATOR_APP in methods
        pending = bool(secret) and not uses_app
        qr_code_svg = setup_key = None
        if pending:
            adapter = get_mfa_adapter()
            qr_code_svg = adapter.build_totp_svg(adapter.build_totp_url(user, secret))
            setup_key = secret
        identities = {identity.provider: identity for identity in UserIdentity.objects.filter(user=user)}
        context = {
            "title": _("Two-factor authentication"),
            "user": user,
            "uses_app": uses_app,
            "uses_email": MfaMethod.EMAIL_CODE in methods,
            "email_codes_allowed": policy.email_codes_allowed(),
            "email_code_sent": bool(request.session.get(EMAIL_CODE_SENT_KEY)),
            "pending": pending,
            "requirement_required": policy.requirement_for(user) == MfaRequirement.REQUIRED,  # type: ignore[arg-type]
            "enrolled": methods != [],
            "qr_code_svg": qr_code_svg,
            "setup_key": setup_key,
            "recovery_codes": [],
            "remember_device_days": policy.remember_device_days(),
            "device_trusted": (
                TrustedDevices(policy).is_trusted(request, user)  # type: ignore[arg-type]
                and not extra.get("device_forgotten")
            ),
            "sso_providers": [
                {
                    "provider": provider,
                    "identity": identities.get(provider.key),
                    "link_url": _sso_link_url(provider.key),
                }
                for provider in enabled_providers()
            ],
            "errors": errors or {},
            **extra,
        }
        template = f"{TEMPLATE}#{partial}" if partial else TEMPLATE
        return render(request, template, context)


def _sso_link_url(key: str) -> str | None:
    """Link button target once the SSO sign-in routes exist (Phase 2)."""
    try:
        return f"{reverse('sso_redirect', args=[key])}?link=1"
    except NoReverseMatch:
        return None


security = SecurityView.as_view()
