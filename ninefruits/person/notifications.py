"""Person mails (original ``AccountInvitationNotification``)."""

from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.utils import formats, timezone, translation
from django.utils.translation import gettext as _


def send_account_invitation(email: str, url: str, expires_at: datetime) -> None:
    """Invitation link to create an account (the person has no account, so no locale yet)."""
    with translation.override(translation.get_language() or settings.LANGUAGE_CODE):
        app = settings.APP_NAME
        lines = [
            _("Hello,"),
            "",
            _("Your school has invited you to create an account."),
            "",
            f"{_('Create account')}: {url}",
            "",
            _("This link works until %(date)s.")
            % {"date": formats.date_format(timezone.localtime(expires_at), "DATE_FORMAT")},
            "",
            _("Thank you,\n%(app)s") % {"app": app},
        ]
        send_mail(_("Create your %(app)s account") % {"app": app}, "\n".join(lines), None, [email])
