"""``security_reencrypt_secrets``: after a ``DJANGO_SECRET_KEY`` rotation, writes the secrets
encrypted with a key derived from it (``ninefruits.security.crypto``) again with the current key:
authenticator app secrets, recovery code seeds and SSO client secrets. Until then they are read
with the previous key in ``DJANGO_SECRET_KEY_FALLBACKS``; run this before removing it
(``operations/security-keys.md``). The original rotated ``APP_KEY`` with ``APP_PREVIOUS_KEYS``
and had no such step, because Laravel's encrypter reads with the previous keys on every request."""

from __future__ import annotations

from typing import Any

from allauth.mfa.models import Authenticator
from django.core.management.base import CommandParser
from django.db import transaction

from ninefruits.core.commands import AuditedCommand
from ninefruits.security.crypto import reencrypt_string, uses_current_key
from ninefruits.settings.groups.authentication import AuthenticationSettings

#: allauth authenticator data keys written with the MFA adapter's ``encrypt``.
_ENCRYPTED_DATA = {Authenticator.Type.TOTP: ("secret",), Authenticator.Type.RECOVERY_CODES: ("seed",)}


class Command(AuditedCommand):
    help = "Re-encrypt two-factor and SSO secrets with the current DJANGO_SECRET_KEY after a key rotation"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--dry-run", action="store_true", help="Count secrets still encrypted with a previous key")

    def handle(self, *args: Any, **options: Any) -> int:  # type: ignore[override]  # exit code (StatusCommand)
        dry_run = self.is_dry_run()
        try:
            with transaction.atomic():
                authenticators = self._authenticators(dry_run)
                providers = self._sso_providers(dry_run)
        except ValueError:
            self.error(
                "A secret cannot be decrypted with DJANGO_SECRET_KEY or DJANGO_SECRET_KEY_FALLBACKS. "
                "Put the previous key in DJANGO_SECRET_KEY_FALLBACKS and run again."
            )
            return self.FAILURE
        self.record_result({"authenticators": authenticators, "sso_providers": providers})
        prefix = "Dry run: " if dry_run else ""
        verb = "use a previous key" if dry_run else "re-encrypted"
        self.info(f"{prefix}{authenticators} authenticator(s) and {providers} SSO client secret(s) {verb}.")
        return self.SUCCESS

    def _authenticators(self, dry_run: bool) -> int:
        changed = 0
        rows = Authenticator.objects.filter(type__in=list(_ENCRYPTED_DATA)).order_by("pk")
        for authenticator in rows.select_for_update().iterator(chunk_size=500):
            data = dict(authenticator.data)
            outdated = False
            for key in _ENCRYPTED_DATA[authenticator.type]:
                if isinstance(data.get(key), str) and not uses_current_key(data[key]):
                    data[key] = reencrypt_string(data[key])
                    outdated = True
            codes = data.get("migrated_codes")
            if isinstance(codes, list) and not all(uses_current_key(str(code)) for code in codes):
                data["migrated_codes"] = [reencrypt_string(str(code)) for code in codes]
                outdated = True
            if outdated:
                changed += 1
                if not dry_run:
                    authenticator.data = data
                    authenticator.save(update_fields=["data"])
        return changed

    def _sso_providers(self, dry_run: bool) -> int:
        settings = AuthenticationSettings.load()
        providers = [dict(provider) for provider in settings.sso_providers]
        changed = 0
        for provider in providers:
            secret = provider.get("client_secret")
            if isinstance(secret, str) and secret and not uses_current_key(secret):
                provider["client_secret"] = reencrypt_string(secret)
                changed += 1
        if changed and not dry_run:
            settings.sso_providers = providers
            settings.save()
        return changed
