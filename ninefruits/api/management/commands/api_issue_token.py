"""Issues an integration token for an account (ADR 0004-django), typically a service account
of an LMS or a BI tool holding only the permissions it needs (``lms.manage``, ``reports.view``).
The token is printed once; only its digest is stored."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import CommandParser

from ninefruits.api.actions import MAX_TOKEN_DAYS, IssueApiToken
from ninefruits.core.commands import AuditedCommand


class Command(AuditedCommand):
    help = "Issue an API integration token for an account (printed once)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("email", help="Email of the account the token acts as")
        parser.add_argument(
            "--days", type=int, default=None, help=f"Lifetime in days (1-{MAX_TOKEN_DAYS}; default API_TOKEN_TTL_DAYS)"
        )
        parser.add_argument("--reason", default=None, help="What the token is for (recorded in the audit)")

    def handle(self, *args: Any, **options: Any) -> int:
        from ninefruits.security.models import User

        user = User.objects.filter(email=options["email"]).first()
        if user is None:
            self.error("Unknown account.")
            return self.FAILURE
        try:
            issued = IssueApiToken()(user, None, options.get("days"), options.get("reason"), causer=self.actor())
        except ValidationError as error:
            for message in error.messages:
                self.error(message)
            return self.FAILURE
        self.record_result(
            {
                "user_id": user.pk,
                "key_prefix": issued.key,
                "expires_at": issued.expires_at.isoformat() if issued.expires_at else None,
            }
        )
        self.stdout.write(issued.token)
        self.detail("Key", issued.key)
        self.detail("Expires", issued.expires_at.isoformat() if issued.expires_at else "never")
        self.warn("Store the token now: it cannot be shown again. Send it as: Authorization: Token <token>")
        return self.SUCCESS
