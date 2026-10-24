from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from ninefruits.registration.data import RegistrationContext, RuleCheck
from ninefruits.registration.enums import AttemptAction, RuleCode
from ninefruits.term.enums import TermWindowType
from ninefruits.term.services import TermResolver

from .base import RegistrationRule


def window_failed(action: AttemptAction) -> str:
    messages = {
        AttemptAction.ENROLL: _("Registration is not open for you now."),
        AttemptAction.WAITLIST: _("Registration is not open for you now."),
        AttemptAction.DROP: _("Dropping is not open for this course now."),
        AttemptAction.WITHDRAW: _("Withdrawal is not open for this course now."),
        AttemptAction.PROMOTE: _("Registration is not open for this course now."),
        AttemptAction.CART: _("The cart is not open for you now."),
    }
    return messages[AttemptAction(action)]


class WindowRule(RegistrationRule):
    """The action must fall in an open window for the student: registration (term) or add/drop
    (the section's session) to enroll or drop, the cart window to plan, withdrawal (session) to
    withdraw. Staff adjustments waive it."""

    code = RuleCode.WINDOW

    def __init__(self, terms: TermResolver | None = None) -> None:
        self.terms = terms or TermResolver()

    def applies_to(self, action: AttemptAction) -> bool:
        return True

    def check(self, context: RegistrationContext, parameters: dict[str, Any]) -> RuleCheck:
        section = context.section

        def term_open(window_type: TermWindowType) -> bool:
            return any(
                term.pk == section.term_id
                for term in self.terms.terms_open_for(window_type, context.record, context.at)
            )

        def session_open(window_type: TermWindowType) -> bool:
            return self.terms.is_open_in_session(window_type, section.session, context.record, context.at)

        if context.action == AttemptAction.CART:
            is_open = term_open(TermWindowType.REGISTRATION_CART) or term_open(TermWindowType.REGISTRATION)
        elif context.action == AttemptAction.WITHDRAW:
            is_open = session_open(TermWindowType.WITHDRAWAL)
        else:
            is_open = term_open(TermWindowType.REGISTRATION) or session_open(TermWindowType.ADD_DROP)
        return RuleCheck.ok() if is_open else RuleCheck.fail(window_failed(context.action))
