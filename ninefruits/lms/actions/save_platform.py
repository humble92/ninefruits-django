"""Creates or changes an LMS platform (original Filament ``CreateLmsPlatform``/``EditLmsPlatform``).

Credentials are written, never shown: an empty value on edit keeps the stored ones. Every change
is in the data audit with the credentials column masked (secret column of the trigger)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import transaction

from ninefruits.lms.models import LmsPlatform
from ninefruits.security.enums import Permission


class SavePlatform:
    def __call__(self, platform: LmsPlatform, actor: Any, credentials: dict[str, str] | None = None) -> LmsPlatform:
        return self.handle(platform, actor, credentials)

    def handle(self, platform: LmsPlatform, actor: Any, credentials: dict[str, str] | None = None) -> LmsPlatform:
        """``platform`` carries the other fields already; ``credentials`` replaces the stored ones
        when it has any value."""
        if not actor.has_perm(Permission.LMS_MANAGE):
            raise PermissionDenied
        cleaned = {str(key).strip(): str(value) for key, value in (credentials or {}).items() if str(key).strip()}
        if cleaned:
            platform.credentials = cleaned
        if platform.options is None:
            platform.options = {}
        with transaction.atomic():
            platform.save()
        return platform
