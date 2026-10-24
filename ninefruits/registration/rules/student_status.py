from __future__ import annotations

from typing import Any

from django.utils.translation import gettext as _

from ninefruits.person.enums import StudentStatus
from ninefruits.registration.data import RegistrationContext, RuleCheck
from ninefruits.registration.enums import RuleCode

from .base import RegistrationRule, RuleDefaults


class StudentStatusRule(RegistrationRule):
    """Only records in the allowed statuses register (default: enrolled; on leave cannot).
    Parameter ``statuses``."""

    code = RuleCode.STUDENT_STATUS

    def defaults(self) -> RuleDefaults:
        return RuleDefaults(parameters={"statuses": [StudentStatus.ENROLLED.value]})

    def check(self, context: RegistrationContext, parameters: dict[str, Any]) -> RuleCheck:
        allowed = parameters.get("statuses") or [StudentStatus.ENROLLED.value]
        if not isinstance(allowed, list | tuple):
            allowed = [allowed]
        if context.record.status in [str(status) for status in allowed]:
            return RuleCheck.ok()
        return RuleCheck.fail(
            _("Your status (%(status)s) does not allow registration.")
            % {"status": StudentStatus(context.record.status).label}
        )
