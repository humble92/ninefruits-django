"""Create a user with the System Administrator role (initial installation). Original
``security:create-administrator``."""

from __future__ import annotations

import getpass
import sys
from typing import Any

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import CommandParser
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from ninefruits.core.commands import AuditedCommand
from ninefruits.security.actions import AssignRole
from ninefruits.security.models import Role, User


class Command(AuditedCommand):
    help = "Create a user with the System Administrator role (initial installation)"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--email")
        parser.add_argument("--name")
        parser.add_argument(
            "--password-stdin",
            action="store_true",
            help="Read the password from standard input (non-interactive installs)",
        )

    def handle(self, *args: Any, **options: Any) -> int:
        role = Role.objects.filter(name="system_administrator").first()
        if role is None:
            self.error(
                "The system_administrator role is missing. Run uv run manage.py setup_install or the "
                "essential seeders first."
            )
            return self.FAILURE

        interactive = sys.stdin.isatty()
        name = options.get("name") or (input("Name: ").strip() if interactive else "")
        email = (options.get("email") or (input("Email: ").strip() if interactive else "")).lower()
        if options["password_stdin"]:
            secret = sys.stdin.readline().strip()
        elif interactive:
            secret = getpass.getpass("Password: ")
        else:
            self.error("Run interactively or pass --password-stdin.")
            return self.FAILURE
        if not name or not email:
            self.error("--name and --email are required.")
            return self.FAILURE

        try:
            validate_email(email)
            if User.objects.filter(email=email).exists():
                raise ValidationError("The email has already been taken.")
            validate_password(secret, User(email=email, name=name))
        except ValidationError as error:
            self.error(error.messages[0])
            return self.FAILURE

        with transaction.atomic():
            user = User.objects.create_user(email=email, password=secret, name=name)
            user.email_verified_at = timezone.now().replace(microsecond=0)
            user.save(update_fields=["email_verified_at", "updated_at"])
            AssignRole()(
                user,
                role,
                "Initial administrator created by security_create_administrator",
                assigned_by=self.actor(),
                enforce_actor_limits=False,
            )

        self.record_result({"user_id": user.pk, "email": email})
        self.info(f"Administrator {email} created.")
        return self.SUCCESS
