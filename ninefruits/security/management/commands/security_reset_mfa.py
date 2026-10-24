"""Reset a user's two-factor authentication. Original ``security:reset-mfa``: for when no
administrator can sign in to the admin panel (e.g. the only administrator lost their phone).
Otherwise use the reset action on the user screen."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.security.actions import ResetUserMfa
from ninefruits.security.models import User


class Command(AuditedCommand):
    help = "Reset a user's two-factor authentication. Requires --reason and --actor."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("user", help="Email of the user")
        parser.add_argument("--reason", help="Why the reset is needed (required)")

    def handle(self, *args: Any, **options: Any) -> int:
        user = User.objects.filter(email=str(options["user"]).lower()).first()
        reason = (options.get("reason") or "").strip()
        actor = self.actor()
        if user is None:
            self.error("No user with that email.")
            return self.FAILURE
        if not reason or actor is None:
            self.error("--reason and --actor are required.")
            return self.FAILURE
        ResetUserMfa()(user, reason, actor)
        self.record_result({"user_id": user.pk})
        self.info(f"Two-factor authentication reset for {user.email}. They enroll again at the next sign-in.")
        return self.SUCCESS
