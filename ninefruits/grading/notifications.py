"""Grading mails (original ``GradesReturnedNotification``, ``MissingGradesNotification``,
``EvaluationMethodDecidedNotification``, ``GradeExceptionNotification``) and the term close
completion notice (porting-plan 13.1). Each is sent in the recipient's language; recipients
without an email address are skipped."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from ninefruits.grading.enums import EvaluationMethod, RequestStatus


def _absolute(path: str) -> str:
    base = str(getattr(settings, "APP_URL", "") or "").rstrip("/")
    return f"{base}{path}"


def section_title(section: Any) -> str:
    return f"{section.label()} {section.version.title or ''}".strip()


def _send(user: Any, subject: str, lines: list[str], link_label: str, link: str) -> bool:
    body = [
        _("Hello,"),
        "",
        *lines,
        "",
        f"{link_label}: {_absolute(link)}",
        "",
        _("Thank you,\n%(app)s") % {"app": settings.APP_NAME},
    ]
    send_mail(subject, "\n".join(body), None, [user.email])
    return True


def _language(user: Any) -> str:
    return getattr(user, "locale", None) or translation.get_language() or settings.LANGUAGE_CODE


def send_grades_returned(user: Any, section: Any, reason: str) -> bool:
    """Tells an instructor that staff returned the section's submitted grades, and why."""
    if user is None or not user.email:
        return False
    with translation.override(_language(user)):
        label = section_title(section)
        return _send(
            user,
            _("Grades returned: %(section)s") % {"section": label},
            [
                _("The grades of %(section)s were returned to you. Please check them and submit again.")
                % {"section": label},
                reason,
            ],
            _("Open grade entry"),
            reverse("portal:grade_entry", args=[section.pk]),
        )


def send_missing_grades(user: Any, sections: Iterable[Any]) -> bool:
    """Reminds an instructor of sections whose grades are not submitted yet."""
    if user is None or not user.email:
        return False
    with translation.override(_language(user)):
        return _send(
            user,
            _("Grades not submitted yet"),
            [
                _("These sections still have grades that are not submitted:"),
                *(f"- {section_title(section)}" for section in sections),
            ],
            _("Open my teaching"),
            reverse("portal:teaching"),
        )


def send_method_decided(request: Any, drafts_cleared: int) -> bool:
    """Tells the instructor that their evaluation method request was approved or rejected."""
    user = request.requested_by
    if user is None or not user.email:
        return False
    with translation.override(_language(user)):
        label = section_title(request.section)
        method = str(EvaluationMethod(request.requested_method).label)
        approved = request.status == RequestStatus.APPROVED
        if approved:
            subject = _("Evaluation method changed: %(section)s") % {"section": label}
            lines = [_("%(section)s is now evaluated by %(method)s.") % {"section": label, "method": method}]
        else:
            subject = _("Evaluation method request rejected: %(section)s") % {"section": label}
            lines = [
                _("The request to evaluate %(section)s by %(method)s was rejected.")
                % {"section": label, "method": method}
            ]
        if request.decision_note:
            lines.append(request.decision_note)
        if approved and drafts_cleared > 0:
            lines.append(
                _("%(count)s draft grade(s) entered under the old method were cleared; please enter them again.")
                % {"count": drafts_cleared}
            )
        return _send(
            user, subject, lines, _("Open grade entry"), reverse("portal:grade_entry", args=[request.section_id])
        )


def send_grade_exception(user: Any, section: Any, submitted_by: Any, reason: str, violations: list[str]) -> bool:
    """Tells a reviewer (department heads, the academic office) that staff submitted a section's
    relative grades outside the grade caps, and why."""
    if user is None or not user.email:
        return False
    with translation.override(_language(user)):
        label = section_title(section)
        return _send(
            user,
            _("Grades submitted outside the caps: %(section)s") % {"section": label},
            [
                _("%(user)s submitted the grades of %(section)s outside the institution's grade caps.")
                % {"user": submitted_by.email, "section": label},
                f"{pgettext('common', 'Reason')}: {reason}",
                *(f"- {violation}" for violation in violations),
            ],
            _("Open grade entry"),
            reverse("portal:grade_entry", args=[section.pk]),
        )


def send_term_closed(user: Any, term: Any, counts: dict[str, int]) -> bool:
    """Tells the staff member who started a term close that it finished (porting-plan 13.1)."""
    if user is None or not user.email:
        return False
    with translation.override(_language(user)):
        return _send(
            user,
            _("Term closed: %(term)s") % {"term": str(term.name)},
            [
                _("The term close of %(term)s finished. The term is now grades closed.") % {"term": str(term.name)},
                _(
                    "%(records)s term record(s), %(warnings)s academic warning(s), %(dismissal_reviews)s dismissal "
                    "review(s), %(honors)s honors student(s)."
                )
                % counts,
            ],
            _("Open term records"),
            reverse("admin:grading_termrecord_changelist") + f"?term={term.pk}",
        )
