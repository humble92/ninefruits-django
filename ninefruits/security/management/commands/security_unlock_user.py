"""Release an account locked after failed sign-ins. Original ``security:unlock-user``."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.security.actions import UnlockUser
from ninefruits.security.models import User


class Command(AuditedCommand):
    help = "Release an account locked after failed sign-ins. Requires --reason."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("user", help="Email of the user")
        parser.add_argument("--reason", help="Why the lock is released early (required)")

    def handle(self, *args: Any, **options: Any) -> int:
        user = User.objects.filter(email=str(options["user"]).lower()).first()
        reason = (options.get("reason") or "").strip()
        if user is None:
            self.error("No user with that email.")
            return self.FAILURE
        if not reason:
            self.error("--reason is required.")
            return self.FAILURE
        if not user.is_locked() and user.failed_login_count == 0:
            self.info("The account is not locked.")
            return self.SUCCESS
        UnlockUser()(user, reason, self.actor())
        self.record_result({"user_id": user.pk})
        self.info(f"Unlocked {user.email}.")
        return self.SUCCESS
