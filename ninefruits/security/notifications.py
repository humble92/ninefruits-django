"""Security mails (original ``TwoFactorEmailCodeNotification``). Sent immediately, not queued:
the user is waiting on the challenge screen."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.mail import send_mail
from django.utils import translation
from django.utils.translation import gettext as _

if TYPE_CHECKING:
    from ninefruits.security.models import User


def send_two_factor_email_code(user: User, code: str, lifetime_minutes: int) -> None:
    with translation.override(user.locale or translation.get_language() or settings.LANGUAGE_CODE):
        lines = [
            _("Hello,"),
            "",
            _("Use this code to finish signing in:"),
            "",
            code,
            "",
            _("The code expires in %(minutes)s minutes and can be used once.") % {"minutes": lifetime_minutes},
            _("If you did not try to sign in, change your password."),
            "",
            _("Thank you,\n%(app)s") % {"app": settings.APP_NAME},
        ]
        send_mail(_("Your sign-in code"), "\n".join(lines), None, [user.email])
