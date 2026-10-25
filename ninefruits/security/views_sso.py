"""Sign-in and account linking with a school OIDC provider (original ``SsoController``,
porting-plan 7.1, ADR 0007).

- ``/auth/sso/<provider>/redirect/``: starts the flow. Signed-in users with ``?link=1`` link the
  school account to their own account, which needs a recent password confirmation.
- ``/auth/sso/<provider>/callback/``: verifies the ID token, then links (intent ``link``) or signs
  in. A sign-in finds the account through ``user_identities``; with the link mode
  ``institutional_email`` an unlinked school account whose verified email is a student record's
  school email is linked automatically. SSO never creates accounts.

The two-factor policy applies to SSO sign-ins: unless the provider is trusted for two-factor,
enrolled users get the usual challenge (allauth login stages, ``TwoFactorChallengeStage``)."""

from __future__ import annotations

import logging
import secrets
from typing import Any

from allauth.account.internal.flows.login import perform_login, record_authentication
from allauth.account.internal.flows.reauthentication import did_recently_reauthenticate
from allauth.account.models import Login
from django.contrib import messages
from django.db import connection
from django.http import Http404, HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views import View
from django_ratelimit.decorators import ratelimit

from ninefruits.audit.security_events import SecurityEventType, record_security_event
from ninefruits.security.actions.identities import LinkIdentity
from ninefruits.security.enums import SsoLinkMode
from ninefruits.security.models import User, UserIdentity
from ninefruits.security.services.oidc import OidcClient, OidcError
from ninefruits.security.services.sso import OidcProvider
from ninefruits.security.services.sso import provider as find_provider

logger = logging.getLogger(__name__)

SESSION_PREFIX = "sso."
LOGIN_BACKEND = "ninefruits.security.backends.LoginIdentifierBackend"
#: ``Login.state`` flag read by ``TwoFactorChallengeStage``.
TRUSTS_MFA_STATE = "sso_trusts_mfa"

#: Tests replace this to talk to a fake provider.
oidc_client_factory = OidcClient


def _provider_or_404(key: str) -> OidcProvider:
    config = find_provider(key)
    if config is None:
        raise Http404
    return config


def _callback_url(request: HttpRequest, config: OidcProvider) -> str:
    return request.build_absolute_uri(reverse("sso_callback", args=[config.key]))


def _fail(request: HttpRequest, message: str) -> HttpResponse:
    messages.error(request, message)
    return redirect("account_login")


@method_decorator(ratelimit(key="ip", rate="20/m", block=True), name="dispatch")
class SsoRedirectView(View):
    def get(self, request: HttpRequest, provider: str) -> HttpResponse:
        config = _provider_or_404(provider)
        intent = "link" if request.user.is_authenticated and request.GET.get("link") else "login"

        # Linking changes how the account can be entered: require a recent password confirmation.
        if intent == "link" and not did_recently_reauthenticate(request):
            return redirect(f"{reverse('account_reauthenticate')}?next={reverse('portal:security')}")

        state = secrets.token_urlsafe(30)
        nonce = secrets.token_urlsafe(30)
        verifier = secrets.token_urlsafe(48)
        request.session[f"{SESSION_PREFIX}{state}"] = {
            "provider": config.key,
            "nonce": nonce,
            "verifier": verifier,
            "intent": intent,
            "user_id": request.user.pk if request.user.is_authenticated else None,
        }
        try:
            url = oidc_client_factory().authorization_url(
                config, _callback_url(request, config), state, nonce, verifier
            )
        except OidcError:
            logger.exception("sso.discovery_failed", extra={"provider": config.key})
            return _fail(request, _("School sign-in failed. Try again or sign in with your password."))
        return HttpResponseRedirect(url)


@method_decorator(ratelimit(key="ip", rate="20/m", block=True), name="dispatch")
class SsoCallbackView(View):
    def get(self, request: HttpRequest, provider: str) -> HttpResponse:
        config = _provider_or_404(provider)
        attempt: Any = request.session.pop(f"{SESSION_PREFIX}{request.GET.get('state', '')}", None)
        if not isinstance(attempt, dict) or attempt.get("provider") != config.key:
            return _fail(request, _("The sign-in attempt expired. Try again."))
        code = request.GET.get("code")
        if not code:
            return _fail(request, _("Sign-in was cancelled."))

        try:
            claims = oidc_client_factory().exchange(
                config, code, _callback_url(request, config), attempt["verifier"], attempt["nonce"]
            )
        except OidcError:
            logger.warning("sso.token_rejected", extra={"provider": config.key}, exc_info=True)
            return _fail(request, _("School sign-in failed. Try again or sign in with your password."))

        subject = str(claims["sub"])
        claimed_email = claims.get("email")
        email = claimed_email.lower() if isinstance(claimed_email, str) else None
        email_verified = claims.get("email_verified") in (True, "true")

        if attempt.get("intent") == "link":
            return self._link(request, config, attempt, subject, email)
        return self._sign_in(request, config, subject, email, email_verified)

    def _link(
        self, request: HttpRequest, config: OidcProvider, attempt: dict[str, Any], subject: str, email: str | None
    ) -> HttpResponse:
        if not request.user.is_authenticated or request.user.pk != attempt.get("user_id"):
            return _fail(request, _("The sign-in attempt expired. Try again."))
        from django.core.exceptions import ValidationError

        try:
            LinkIdentity()(request.user, config.key, subject, email, "manual")
        except ValidationError as error:
            for message in error.messages:
                messages.error(request, message)
            return redirect("portal:security")
        messages.success(request, _("%(provider)s account linked.") % {"provider": config.label})
        return redirect("portal:security")

    def _sign_in(
        self, request: HttpRequest, config: OidcProvider, subject: str, email: str | None, email_verified: bool
    ) -> HttpResponse:
        from ninefruits.settings.groups.authentication import AuthenticationSettings

        identity = UserIdentity.objects.filter(provider=config.key, subject=subject).select_related("user").first()
        user: User | None = identity.user if identity is not None else None

        settings = AuthenticationSettings.load()
        if (
            user is None
            and settings.sso_link_mode == SsoLinkMode.INSTITUTIONAL_EMAIL
            and email is not None
            and email_verified
        ):
            with connection.cursor() as cursor:
                cursor.execute("SELECT util.user_id_for_institutional_email(%s)", [email])
                row = cursor.fetchone()
            user = User.objects.filter(pk=row[0]).first() if row and row[0] is not None else None
            if user is not None:
                identity = LinkIdentity()(user, config.key, subject, email, "institutional_email")

        if user is None:
            return _fail(
                request,
                _(
                    "Your %(provider)s account is not linked to an account here. Sign in with your password and "
                    "link it under Security."
                )
                % {"provider": config.label},
            )

        if not user.is_active or user.is_locked():
            record_security_event(SecurityEventType.LOGIN_FAILED, user=user, identifier=f"sso:{config.key}")
            return _fail(request, _("These credentials do not match our records."))

        if identity is not None:
            identity.last_used_at = timezone.now().replace(microsecond=0)
            identity.save(update_fields=["last_used_at", "updated_at"])

        user.backend = LOGIN_BACKEND
        record_authentication(request, user, method="socialaccount", provider=config.key, uid=subject)
        login = Login(user=user, redirect_url=reverse("portal:dashboard"))
        login.state[TRUSTS_MFA_STATE] = config.trusts_mfa
        response: HttpResponse = perform_login(request, login)
        return response
