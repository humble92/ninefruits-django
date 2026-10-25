"""Registration policies (original ``App\\Policies\\Registration\\*``). Registered from
``RegistrationConfig.ready``."""

from __future__ import annotations

from typing import Any

from ninefruits.institution.policies import ReferenceDataPolicy
from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class EnrollmentPolicy(Policy):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.ENROLLMENTS_VIEW) or user.has_perm(Permission.REGISTRATION_MANAGE))

    def view(self, user: Any, obj: Any) -> bool:
        from ninefruits.registration.models import Enrollment

        return obj is not None and Enrollment.objects.visible_to(user).filter(pk=obj.pk).exists()

    def create(self, user: Any, obj: Any) -> bool:
        """Staff registrations go through the registration actions (rules, seats, reasons)."""
        return bool(user.has_perm(Permission.REGISTRATION_MANAGE))

    def update(self, user: Any, obj: Any) -> bool:
        return obj is not None and obj.section.is_registration_manageable_by(user)

    def delete(self, user: Any, obj: Any) -> bool:
        return False


class WaitlistEntryPolicy(EnrollmentPolicy):
    def view(self, user: Any, obj: Any) -> bool:
        from ninefruits.registration.models import WaitlistEntry

        return obj is not None and WaitlistEntry.objects.visible_to(user).filter(pk=obj.pk).exists()


class RegistrationAttemptPolicy(Policy):
    """The attempt log is read only."""

    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.REGISTRATION_MANAGE) or user.has_perm(Permission.ENROLLMENTS_VIEW))

    def view(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)

    def create(self, user: Any, obj: Any) -> bool:
        return False

    def update(self, user: Any, obj: Any) -> bool:
        return False

    def delete(self, user: Any, obj: Any) -> bool:
        return False


class RegistrationHoldPolicy(Policy):
    """Holds and overrides: released or revoked, never deleted."""

    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(
            user.has_perm(Permission.REGISTRATION_HOLDS_MANAGE) or user.has_perm(Permission.REGISTRATION_MANAGE)
        )

    def view(self, user: Any, obj: Any) -> bool:
        return self.view_any(user, obj)

    def create(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.REGISTRATION_HOLDS_MANAGE))

    def update(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.REGISTRATION_HOLDS_MANAGE))

    def delete(self, user: Any, obj: Any) -> bool:
        return False


class RegistrationRulePolicy(ReferenceDataPolicy):
    """Rule sets, rules and credit limit policies."""

    def __init__(self) -> None:
        super().__init__(Permission.REGISTRATION_RULES_MANAGE)


def register_policies() -> None:
    register("registration.enrollment", EnrollmentPolicy())
    register("registration.waitlistentry", WaitlistEntryPolicy())
    register("registration.registrationattempt", RegistrationAttemptPolicy())
    register("registration.registrationhold", RegistrationHoldPolicy())
    register("registration.registrationoverride", RegistrationHoldPolicy())
    for label in (
        "registration.registrationruleset",
        "registration.registrationrule",
        "registration.creditlimitpolicy",
    ):
        register(label, RegistrationRulePolicy())
