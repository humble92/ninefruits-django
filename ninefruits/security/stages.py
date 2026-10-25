"""Two-factor step of the allauth login pipeline (original
``RedirectIfTwoFactorChallengeRequired``): asks for any enrolled method (authenticator app or
email code), skipped for devices the user chose to remember. Users whose only method is email
get a code sent right away. TOTP-only users never get the email path."""

from __future__ import annotations

from typing import Any

from allauth.account.stages import LoginStage
from allauth.core.internal.httpkit import headed_redirect_response

from ninefruits.security.enums import MfaMethod


class TwoFactorChallengeStage(LoginStage):  # type: ignore[misc]  # django-allauth has no type information
    key = "ninefruits_two_factor"
    urlname = "security:two_factor_challenge"

    def handle(self) -> tuple[Any, bool]:
        from ninefruits.security.services.email_code import PURPOSE_LOGIN, EmailCodeChallenge
        from ninefruits.security.services.mfa_policy import MfaPolicy
        from ninefruits.security.services.trusted_devices import TrustedDevices

        user = self.login.user
        if user is None:
            return None, True
        # School sign-in with a provider trusted for two-factor (``views_sso``).
        if self.login.state.get("sso_trusts_mfa"):
            return None, True
        policy = MfaPolicy()
        if TrustedDevices(policy).is_trusted(self.request, user):
            return None, True
        methods = policy.methods_for(user)
        if not methods:
            return None, True
        if methods == [MfaMethod.EMAIL_CODE] and not self.state.get("email_code_sent"):
            EmailCodeChallenge().send(user, PURPOSE_LOGIN)
            self.state["email_code_sent"] = True
        self.state["required"] = True
        return headed_redirect_response(self.urlname), True
