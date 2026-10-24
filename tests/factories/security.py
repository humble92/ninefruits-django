"""Factories for accounts and roles (original ``UserFactory`` and ``Security\\RoleFactory``)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import factory
from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import TOTP, format_hotp_value, hotp_value, yield_hotp_counters_from_time
from django.utils import timezone

from ninefruits.security.enums import Permission, Persona, ScopeType
from ninefruits.security.models import Role, User

#: Secret of the authenticator app created by ``UserFactory(with_mfa=True)``.
TWO_FACTOR_TEST_SECRET = "JBSWY3DPEHPK3PXP"
PASSWORD = "password"


def current_otp(secret: str = TWO_FACTOR_TEST_SECRET) -> str:
    counter = next(iter(yield_hotp_counters_from_time()))
    return format_hotp_value(hotp_value(secret, counter))


def enroll_authenticator_app(user: User, secret: str = TWO_FACTOR_TEST_SECRET) -> list[str]:
    """Confirmed authenticator app plus recovery codes; returns the recovery codes."""
    TOTP.activate(user, secret)
    return RecoveryCodes.activate(user).generate_codes()


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Role
        skip_postgeneration_save = True

    name = factory.Sequence(lambda n: f"test_role_{n}")
    guard_name = "web"
    display_name = factory.LazyAttribute(lambda role: {"en": role.name.replace("_", " ").title()})

    class Params:
        persona_of = None

    @factory.lazy_attribute
    def persona(self) -> str | None:
        return str(self.persona_of) if self.persona_of else None

    @factory.post_generation
    def permissions(self, create: bool, extracted: Iterable[Permission | str] | None, **kwargs: Any) -> None:
        if create and extracted:
            self.sync_permissions([str(permission) for permission in extracted])

    @classmethod
    def persona_role(cls, persona: Persona, **kwargs: Any) -> Role:
        return cls(name=persona.value, persona_of=persona, **kwargs)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"user{n}@example.test")
    email_verified_at = factory.LazyFunction(lambda: timezone.now().replace(microsecond=0))
    password = factory.django.Password(PASSWORD)
    remember_token = factory.Faker("pystr", max_chars=10)

    class Params:
        inactive = factory.Trait(is_active=False)
        unverified = factory.Trait(email_verified_at=None)

    @factory.post_generation
    def with_mfa(self, create: bool, extracted: bool | None, **kwargs: Any) -> None:
        if create and extracted:
            enroll_authenticator_app(self)

    @factory.post_generation
    def permissions(self, create: bool, extracted: Iterable[Permission | str] | None, **kwargs: Any) -> None:
        """Assigns a role (global scope unless ``permissions__scope_type``) holding them."""
        if not create or extracted is None:
            return
        from ninefruits.security.actions import AssignRole

        role = RoleFactory(permissions=list(extracted))
        AssignRole()(
            self,
            role,
            "test",
            ScopeType(kwargs.get("scope_type", ScopeType.GLOBAL)),
            kwargs.get("scope_id"),
        )


def has_authenticator_app(user: User) -> bool:
    return Authenticator.objects.filter(user=user, type=Authenticator.Type.TOTP).exists()
