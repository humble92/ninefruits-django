"""Two-factor challenge of the sign-in (original Fortify two-factor challenge and
``TwoFactorEmailChallengeController``). Uses allauth's pending login, so the password step,
remembered devices, security events and the login response are the same for every method."""

from __future__ import annotations

from typing import Any

from allauth.account.internal.decorators import login_stage_required
from allauth.account.internal.flows.login import record_authentication
from allauth.mfa.base.forms import AuthenticateForm
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseBase
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View

from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.security.enums import MfaMethod
from ninefruits.security.services.email_code import PURPOSE_LOGIN, EmailCodeChallenge
from ninefruits.security.services.mfa_policy import MfaPolicy
from ninefruits.security.services.trusted_devices import TrustedDevices
from ninefruits.security.stages import TwoFactorChallengeStage

TEMPLATE = "mfa/two_factor_challenge.html"


@method_decorator(
    login_stage_required(stage=TwoFactorChallengeStage.key, redirect_urlname="account_login"), name="dispatch"
)
class TwoFactorStageView(View):
    """Base: the user waiting for the second step."""

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponseBase:
        self.stage = request._login_stage  # type: ignore[attr-defined]
        self.user = self.stage.login.user
        self.policy = MfaPolicy()
        self.methods = self.policy.methods_for(self.user)
        return super().dispatch(request, *args, **kwargs)

    def render_challenge(self, request: HttpRequest, **context: Any) -> HttpResponse:
        context.setdefault("form", AuthenticateForm(user=self.user))
        return render(
            request,
            TEMPLATE,
            {
                "uses_app": MfaMethod.AUTHENTICATOR_APP in self.methods,
                "uses_email": MfaMethod.EMAIL_CODE in self.methods,
                "title": _("Two-factor authentication"),
                **context,
            },
        )

    def complete(self, request: HttpRequest) -> HttpResponse:
        response: HttpResponse = self.stage.exit()
        if request.POST.get("remember_device"):
            TrustedDevices(self.policy).remember(response, self.user)
        return response


class TwoFactorChallengeView(TwoFactorStageView):
    """Authenticator app code or recovery code."""

    def get(self, request: HttpRequest) -> HttpResponse:
        return self.render_challenge(request)

    def post(self, request: HttpRequest) -> HttpResponse:
        if MfaMethod.AUTHENTICATOR_APP not in self.methods:
            raise PermissionDenied
        data = request.POST.copy()
        if not data.get("code") and data.get("recovery_code"):
            data["code"] = data["recovery_code"]
        form = AuthenticateForm(user=self.user, data=data)
        if not form.is_valid():
            return self.render_challenge(request, form=form)
        form.save()
        return self.complete(request)


class TwoFactorEmailChallengeView(TwoFactorStageView):
    """Second step with an emailed one-time code."""

    def post(self, request: HttpRequest) -> HttpResponse:
        if MfaMethod.EMAIL_CODE not in self.methods:
            raise PermissionDenied
        code = request.POST.get("email_code", "").strip()
        if not (len(code) == 6 and code.isdigit()):
            return self.render_challenge(request, email_error=_("The email code must be 6 digits."))
        if not EmailCodeChallenge().verify(self.user, PURPOSE_LOGIN, code):
            record_security_event(SecurityEventType.MFA_CHALLENGE_FAILED, user=self.user)
            return self.render_challenge(request, email_error=_("The code is invalid or has expired."))
        record_authentication(request, self.user, "mfa", type="email_code")
        return self.complete(request)


class TwoFactorEmailSendView(TwoFactorStageView):
    def post(self, request: HttpRequest) -> HttpResponse:
        if MfaMethod.EMAIL_CODE not in self.methods:
            raise PermissionDenied
        challenge = EmailCodeChallenge()
        if challenge.send(self.user, PURPOSE_LOGIN):
            messages.success(request, _("A new code has been sent to your email."))
        else:
            messages.warning(
                request,
                _("Please wait %(seconds)s seconds before requesting another code.")
                % {"seconds": challenge.seconds_until_resend(self.user)},
            )
        return redirect("security:two_factor_challenge")
