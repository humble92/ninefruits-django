"""Registration mails (original ``WaitlistOutcomeNotification``)."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from ninefruits.registration.enums import WaitlistStatus


def _absolute(path: str) -> str:
    base = str(getattr(settings, "APP_URL", "") or "").rstrip("/")
    return f"{base}{path}"


def send_waitlist_outcome(entry: Any, status: WaitlistStatus | str, note: str | None) -> None:
    """Tells a student they got the seat they waited for, or why they left the waitlist. Does
    nothing when the student has no account."""
    user = getattr(entry.student_record.person, "user", None)
    if user is None or not user.email:
        return
    status = WaitlistStatus(status)
    section = entry.section
    with translation.override(user.locale or translation.get_language() or settings.LANGUAGE_CODE):
        label = f"{section.label()} {section.version.title or ''}".strip()
        subjects = {
            WaitlistStatus.PROMOTED: _("You are registered in %(section)s"),
            WaitlistStatus.REMOVED: _("Waitlist for %(section)s"),
            WaitlistStatus.EXPIRED: _("Waitlist for %(section)s closed"),
        }
        intros = {
            WaitlistStatus.PROMOTED: _(
                "A seat became free in %(section)s and you have been registered from the waitlist."
            ),
            WaitlistStatus.REMOVED: _("You were removed from the waitlist for %(section)s."),
            WaitlistStatus.EXPIRED: _("Registration closed before a seat became free in %(section)s."),
        }
        lines = [_("Hello,"), "", intros[status] % {"section": label}]
        if note:
            lines.append(note)
        lines += [
            "",
            f"{_('Open registration')}: {_absolute(reverse('portal:registration'))}",
            "",
            _("Thank you,\n%(app)s") % {"app": settings.APP_NAME},
        ]
        send_mail(subjects[status] % {"section": label}, "\n".join(lines), None, [user.email])
