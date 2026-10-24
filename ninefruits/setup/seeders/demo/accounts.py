from __future__ import annotations

from django.utils import timezone

from ninefruits.security.actions import AssignRole
from ninefruits.security.models import Role, User
from ninefruits.setup import conf
from ninefruits.setup.seeders.base import Seeder


class DemoAccountSeeder(Seeder):
    """One fixed account per staff role template, e.g. ``registrar@demo.test``. Two-factor
    authentication is left unenrolled so the accounts can be used right away."""

    #: Role name -> account name.
    ACCOUNTS: dict[str, str] = {
        "system_administrator": "Demo Administrator",
        "registrar": "Demo Registrar",
        "academic_affairs": "Demo Academic Affairs",
        "certificate_officer": "Demo Certificate Officer",
        "department_assistant": "Demo Department Assistant",
        "admissions_officer": "Demo Admissions Officer",
    }

    def run(self) -> None:
        for role_name, name in self.ACCOUNTS.items():
            email = self.email_for(role_name)
            role = Role.objects.filter(name=role_name).first()
            if role is None or User.objects.filter(email=email).exists():
                continue
            user = User.objects.create_user(email=email, password=conf.DEMO_PASSWORD, name=name)
            user.email_verified_at = timezone.now().replace(microsecond=0)
            user.save(update_fields=["email_verified_at", "updated_at"])
            AssignRole()(user, role, "Demo account", enforce_actor_limits=False)

    @staticmethod
    def email_for(role_name: str) -> str:
        return f"{role_name.replace('_', '-')}@{conf.DEMO_EMAIL_DOMAIN}"

    @classmethod
    def emails(cls) -> list[str]:
        return [cls.email_for(role_name) for role_name in cls.ACCOUNTS]


def demo_account_emails() -> list[str]:
    return DemoAccountSeeder.emails()
