"""Admission mails (original ``ApplicationSubmittedNotification`` and
``ApplicationDecisionNotification``). Mail only, as in the original: the decision itself is shown
after signing in. Sent after the transaction commits, in the recipient's language."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from ninefruits.admission.enums import ApplicationStatus
from ninefruits.admission.models import Application
from ninefruits.i18n.formatting import format_lll


def application_url(application: Application) -> str:
    return f"{str(settings.APP_URL).rstrip('/')}{reverse('portal:application', args=[application.pk])}"


def _language(user: Any) -> str:
    return (getattr(user, "locale", None) or translation.get_language() or settings.LANGUAGE_CODE).replace("_", "-")


def _send(recipient: str, subject: str, lines: list[str]) -> None:
    send_mail(subject, "\n".join(lines), None, [recipient])


def send_application_submitted(application: Application, applicant: Any) -> None:
    with translation.override(_language(applicant)):
        number = application.application_number or ""
        lines = [
            _("Hello,"),
            "",
            _("We received your application %(number)s for %(program)s (%(cycle)s).")
            % {
                "number": number,
                "program": application.program.name,
                "cycle": application.admission_cycle.name,
            },
            "",
            f"{_('View application')}: {application_url(application)}",
            "",
            _("Thank you,\n%(app)s") % {"app": settings.APP_NAME},
        ]
        _send(applicant.email, _("Application %(number)s received") % {"number": number}, lines)


def send_application_decision(application: Application) -> None:
    """To the applicant's account, or to the person's contact email when there is no account."""
    from ninefruits.security.models import User

    user = User.objects.filter(person_id=application.person_id).first()
    recipient = user.email if user is not None else application.person.email
    if not recipient:
        return
    with translation.override(_language(user)):
        lines = [
            _("Hello,"),
            "",
            _("A decision on your application for %(program)s (%(cycle)s) is available. Sign in to see it.")
            % {"program": application.program.name, "cycle": application.admission_cycle.name},
            "",
            f"{_('View application')}: {application_url(application)}",
        ]
        if application.status == ApplicationStatus.ADMITTED and application.offer_expires_at is not None:
            deadline = format_lll(application.offer_expires_at)
            lines += ["", _("If you are admitted, please answer by %(date)s.") % {"date": deadline}]
        lines += ["", _("Thank you,\n%(app)s") % {"app": settings.APP_NAME}]
        _send(
            recipient,
            _("Decision on application %(number)s") % {"number": application.application_number or ""},
            lines,
        )
