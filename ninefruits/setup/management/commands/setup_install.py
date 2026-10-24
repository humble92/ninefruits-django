"""New installation, safe to run again (original ``setup:install``). Each phase adds its steps
(porting-plan 13.2)."""

from __future__ import annotations

import sys
from decimal import Decimal
from typing import Any
from zoneinfo import available_timezones

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandParser

from ninefruits.core.commands import AuditedCommand
from ninefruits.grading.models import GradeScale
from ninefruits.security.models import RoleAssignment
from ninefruits.settings.groups.institution import InstitutionSettings
from ninefruits.setup.seeders.essential import EssentialSeeder
from ninefruits.setup.seeders.profiles import available_profiles
from ninefruits.setup.seeders.profiles.korean_university import seed_scale_43, seed_scale_45


class Command(AuditedCommand):
    help = (
        "Install or update the system: migrations, essential data, institution settings, first administrator, profiles"
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--institution-name", help="Institution name in the default language")
        parser.add_argument("--locale", help="Default language, e.g. ko")
        parser.add_argument("--timezone", help="IANA time zone, e.g. Asia/Seoul")
        parser.add_argument(
            "--profile", action="append", default=[], help="Profile keys to apply (see ninefruits/setup/conf.py)"
        )
        parser.add_argument(
            "--grade-scale",
            help=(
                "Grade scale of the institution, 4.5 or 4.3, fixed once set (otherwise the scale of the first profile)"
            ),
        )
        parser.add_argument("--admin-email", help="First administrator email (skipped if an administrator exists)")
        parser.add_argument("--admin-name", help="First administrator name")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Run without questions; the administrator password is read from standard input",
        )

    def handle(self, *args: Any, **options: Any) -> int:
        self._interactive = not options["force"] and sys.stdin.isatty()
        if not self._check_keys():
            return self.FAILURE

        call_command("migrate", database="migrator", interactive=False, verbosity=0)
        self.detail("Migrations", "DONE")
        EssentialSeeder()()
        self.detail("Essential data", "DONE")

        self._configure_institution(options)
        if not self._fix_grade_scale(options.get("grade_scale")):
            return self.FAILURE

        profiles = self._apply_profiles(options["profile"])
        administrator_created = self._create_administrator(options)

        self.record_result({"profiles": profiles, "administrator_created": administrator_created})
        self.info("Installation complete.")
        return self.SUCCESS

    # -- steps ------------------------------------------------------------------------------------
    def _check_keys(self) -> bool:
        values = {
            "DJANGO_SECRET_KEY": settings.SECRET_KEY,
            "PII_ENCRYPTION_KEY": getattr(settings, "PII_ENCRYPTION_KEY", ""),
            "PII_HASH_KEY": getattr(settings, "PII_HASH_KEY", ""),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            self.error(
                f"Set these environment variables first: {', '.join(missing)}. See uv run manage.py pii_generate_key."
            )
            return False
        return True

    def _ask(self, kind: str, message: str, **kwargs: Any) -> Any:
        import questionary

        prompt = getattr(questionary, kind)(message, **kwargs)
        return prompt.ask()

    def _configure_institution(self, options: dict[str, Any]) -> None:
        institution = InstitutionSettings.load()
        locales = list(institution.supported_locales)
        locale = options.get("locale") or (
            self._ask("select", "Default language", choices=locales, default=institution.default_locale)
            if self._interactive
            else institution.default_locale
        )
        zones = available_timezones() | {"UTC"}
        zone = options.get("timezone") or (
            self._ask(
                "text",
                "Time zone",
                default=institution.timezone,
                validate=lambda value: value in zones or "Unknown time zone.",
            )
            if self._interactive
            else institution.timezone
        )
        name = options.get("institution_name") or (
            self._ask(
                "text", "Institution name", default=institution.name.get(locale) or institution.name.get("en", "")
            )
            if self._interactive
            else None
        )
        if locale not in locales or zone not in zones:
            self.error("Unsupported language or time zone; institution settings were not changed.")
            return
        institution.default_locale = str(locale)
        institution.timezone = str(zone)
        if name:
            institution.name = {**institution.name, str(locale): str(name)}
        institution.save()
        self.detail("Institution", f"{locale}, {zone}")

    def _fix_grade_scale(self, wanted: str | None) -> bool:
        """The grade scale is the institution's scale for good: grades and GPAs are on it. It is
        chosen here (or by the first profile) and cannot change afterwards."""
        if not wanted:
            return True
        current = GradeScale.objects.filter(is_default=True).first()
        try:
            wanted_points = Decimal(wanted)
        except ArithmeticError:
            wanted_points = Decimal(-1)
        if current is not None:
            if current.max_grade_points != wanted_points:
                self.error(
                    f"The grade scale is fixed at {current.max_grade_points} ({current.code}) and cannot change."
                )
                return False
            self.info(f"Grade scale {current.code} (fixed).")
            return True
        seeders = {"4.5": seed_scale_45, "4.3": seed_scale_43}
        seeder = seeders.get(str(wanted))
        if seeder is None:
            self.error("--grade-scale must be 4.5 or 4.3.")
            return False
        scale = seeder(True)
        self.info(f"Grade scale {scale.code} fixed.")
        return True

    def _apply_profiles(self, chosen: list[str]) -> list[str]:
        available = available_profiles()
        if not chosen and self._interactive and available:
            chosen = (
                self._ask(
                    "checkbox",
                    "Profiles to apply",
                    choices=[f"{profile.key} — {profile.label}: {profile.description}" for profile in available],
                )
                or []
            )
            chosen = [choice.split(" ", 1)[0] for choice in chosen]
        applied = []
        for profile in available:
            if profile.key in chosen:
                profile()()
                self.detail(f"Profile {profile.key}", "DONE")
                applied.append(profile.key)
        for key in sorted(set(chosen) - {profile.key for profile in available}):
            self.warn(f"Unknown profile [{key}] skipped.")
        return applied

    def _create_administrator(self, options: dict[str, Any]) -> bool:
        if RoleAssignment.objects.active().filter(role__name="system_administrator").exists():
            self.detail("Administrator", "exists")
            return False
        arguments: dict[str, Any] = {}
        if options.get("admin_email"):
            arguments["email"] = options["admin_email"]
        if options.get("admin_name"):
            arguments["name"] = options["admin_name"]
        if options["force"]:
            arguments["password_stdin"] = True
        if options.get("actor"):
            arguments["actor"] = options["actor"]
        status = call_command(
            "security_create_administrator", stdout=self.stdout._out, stderr=self.stderr._out, **arguments
        )
        return status == self.SUCCESS
