"""Course evaluation mail (original ``EvaluationReminderNotification``): asks a student to evaluate
the courses still open. Sent in the recipient's language; recipients without an email address
are skipped."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _


def _absolute(path: str) -> str:
    base = str(getattr(settings, "APP_URL", "") or "").rstrip("/")
    return f"{base}{path}"


def _language(user: Any) -> str:
    return getattr(user, "locale", None) or translation.get_language() or settings.LANGUAGE_CODE


def send_evaluation_reminder(user: Any, enrollments: Iterable[Any]) -> bool:
    """``enrollments`` with ``section.course`` and ``version``."""
    if user is None or not user.email:
        return False
    with translation.override(_language(user)):
        lines = [
            _("Hello,"),
            "",
            _("Please evaluate these courses:"),
            *(f"- {e.section.label()} {e.version.title or ''}".rstrip() for e in enrollments),
            "",
            _("Your answers are anonymous."),
            "",
            f"{_('Open course evaluation')}: {_absolute(reverse('portal:evaluations'))}",
            "",
            _("Thank you,\n%(app)s") % {"app": settings.APP_NAME},
        ]
        send_mail(_("Course evaluation is open"), "\n".join(lines), None, [user.email])
    return True
