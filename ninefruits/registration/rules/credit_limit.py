from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils.translation import gettext as _

from ninefruits.registration.data import RegistrationContext, RuleCheck
from ninefruits.registration.enums import RuleCode

from .base import RegistrationRule


def credits_text(value: Decimal | float) -> str:
    """Credits as the original printed them (PHP float: ``21``, ``19.5``)."""
    number = Decimal(str(value)).normalize()
    return format(number, "f")


def limit_message(total: Decimal, limit: Decimal) -> str:
    return _("This would make %(total)s credits; your limit is %(limit)s.") % {
        "total": credits_text(total),
        "limit": credits_text(limit),
    }


class CreditLimitRule(RegistrationRule):
    """Total credits in the term within the applicable credit limit policy (legacy: by admission
    year and nursing, read from student number digits). Courses that do not count toward the
    limit (legacy credit bank codes 009*, 900*) are left out. No matching policy: no limit."""

    code = RuleCode.CREDIT_LIMIT

    def check(self, context: RegistrationContext, parameters: dict[str, Any]) -> RuleCheck:
        from ninefruits.registration.models import CreditLimitPolicy

        version = context.section.version
        policy = CreditLimitPolicy.applicable_to(context.record, context.section.term.term_type_id)
        if policy is None or not version.counts_toward_credit_limit:
            return RuleCheck.ok()
        current = sum(
            (Decimal(e.credits) for e in context.term_enrollments() if e.counts_toward_credit_limit), Decimal(0)
        )
        total = current + Decimal(version.credits)
        limit = Decimal(policy.max_credits)
        details = {"credits": float(total), "max_credits": float(limit), "policy_id": policy.pk}
        if total <= limit:
            return RuleCheck.ok(None, details)
        return RuleCheck.fail(limit_message(total, limit), details)
