from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.term.enums import TermStatus
from ninefruits.term.models import Term


class ChangeTermStatus:
    """The only way a term's operating state changes. Transitions follow
    ``TermStatus.allowed_next()``."""

    def __call__(self, term: Term, status: TermStatus | str, reason: str | None = None, changed_by: Any = None) -> Term:
        status = TermStatus(status)
        current = TermStatus(term.status)
        if not current.can_move_to(status):
            raise ValidationError(
                {
                    "status": _("A term cannot move from %(from)s to %(to)s.")
                    % {"from": current.label, "to": status.label}
                }
            )
        with transaction.atomic():
            term.status = status
            term.save(update_fields=["status", "updated_at"])
            audit(
                "term.status_changed",
                term,
                reason=reason,
                properties={"from": current.value, "to": status.value},
                causer=changed_by,
            )
        return term
