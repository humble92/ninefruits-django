"""Create a fictional demo university (original ``setup:demo``). Never runs in production."""

from __future__ import annotations

import csv
import io
import sys
import time
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import CommandParser
from django.utils.module_loading import import_string

from ninefruits.core.commands import AuditedCommand
from ninefruits.setup import conf
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.demo import DemoSeeder
from ninefruits.setup.seeders.demo.options import is_production

#: File written by ``--student-accounts`` (private storage), read by the load tests.
LOAD_ACCOUNTS_FILE = "load-accounts.csv"


class Command(AuditedCommand):
    help = "Create a fictional demo university. Never runs in production."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--size",
            default="small",
            help="tiny (about 20 students), small (about 100), medium (about 2,000) or large (about 20,000)",
        )
        parser.add_argument("--seed", type=int, help="Random seed for reproducible data")
        parser.add_argument(
            "--force", action="store_true", help="Do not ask for confirmation (still refused in production)"
        )
        parser.add_argument(
            "--student-accounts",
            action="store_true",
            help=f"Give every enrolled student an account (load tests) and write {LOAD_ACCOUNTS_FILE}",
        )

    def handle(self, *args: Any, **options: Any) -> int:
        if is_production():
            self.error("Demo data cannot be created in production.")
            return self.FAILURE

        size = str(options["size"])
        if size not in conf.DEMO_SIZES:
            self.error(f"Size must be one of: {', '.join(conf.DEMO_SIZES)}.")
            return self.FAILURE

        if not options["force"]:
            import questionary

            database = settings.DATABASES["default"]["NAME"]
            confirmed = (
                sys.stdin.isatty()
                and questionary.confirm(f"Create {size} demo data in the [{database}] database?", default=False).ask()
            )
            if not confirmed:
                return self.FAILURE

        seed = options.get("seed")
        started = time.monotonic()
        with use_options(DemoOptions(size, seed)):
            DemoSeeder()()
            accounts = self._student_accounts() if options["student_accounts"] else None
        if accounts is not None:
            self.info(f"{accounts} student account(s) written to {LOAD_ACCOUNTS_FILE} in private storage.")

        self.record_result(
            {
                "size": size,
                "seed": seed,
                "student_accounts": bool(options["student_accounts"]),
                "seconds": round(time.monotonic() - started, 1),
            }
        )
        self.info(f"Demo accounts (password: {conf.DEMO_PASSWORD})")
        for email in self._account_emails():
            self.stdout.write(f"  {email}")
        return self.SUCCESS

    def _account_emails(self) -> list[str]:
        emails: list[str] = []
        for path in DemoSeeder.ACCOUNT_LISTS:
            emails.extend(import_string(path)())
        return emails

    def _student_accounts(self) -> int:
        """Accounts for load tests (operations manual, load testing): one per enrolled student
        who has none, with the demo password. ``DemoSeeder.STUDENT_ACCOUNT_PROVIDERS`` yield the
        ``(email, password)`` pairs (the student records seeder of Phase 2)."""
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["email", "password"])
        count = 0
        for path in DemoSeeder.STUDENT_ACCOUNT_PROVIDERS:
            for email, password in import_string(path)():
                writer.writerow([email, password])
                count += 1
        if default_storage.exists(LOAD_ACCOUNTS_FILE):
            default_storage.delete(LOAD_ACCOUNTS_FILE)
        default_storage.save(LOAD_ACCOUNTS_FILE, ContentFile(buffer.getvalue().encode()))
        return count
