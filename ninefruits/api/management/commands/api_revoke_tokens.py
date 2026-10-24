"""Revokes an account's integration tokens (all, or one by its key prefix)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import CommandParser

from ninefruits.api.actions import RevokeApiTokens, token_rows
from ninefruits.core.commands import AuditedCommand


class Command(AuditedCommand):
    help = "Revoke the API integration tokens of an account (all, or one with --key)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("email", help="Email of the account")
        parser.add_argument("--key", default=None, help="Key prefix of one token (as listed)")
        parser.add_argument("--list", action="store_true", help="List the tokens without revoking")
        parser.add_argument("--reason", default=None, help="Why (recorded in the audit)")

    def handle(self, *args: Any, **options: Any) -> int:
        from ninefruits.security.models import User

        user = User.objects.filter(email=options["email"]).first()
        if user is None:
            self.error("Unknown account.")
            return self.FAILURE
        if options.get("list"):
            for row in token_rows(user):
                expires = row["expires_at"].isoformat() if row["expires_at"] else "never"
                self.detail(row["key"], f"created {row['created_at']:%Y-%m-%d %H:%M}, expires {expires}")
            return self.SUCCESS
        count = RevokeApiTokens()(user, None, options.get("key"), options.get("reason"), causer=self.actor())
        self.record_result({"user_id": user.pk, "revoked": count, "key_prefix": options.get("key")})
        if options.get("key") and count == 0:
            self.error("No token with that key.")
            return self.FAILURE
        self.info(f"{count} token(s) revoked.")
        return self.SUCCESS
