"""SSO identity links (original ``LinkIdentity`` and ``UnlinkIdentity``). One external account
belongs to one user, and a user has at most one link per provider."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.security.models import User, UserIdentity


class LinkIdentity:
    def __call__(self, user: User, provider: str, subject: str, email: str | None, how: str) -> UserIdentity:
        existing: UserIdentity | None = UserIdentity.objects.filter(provider=provider, subject=subject).first()
        if existing is not None and existing.user_id != user.pk:
            raise ValidationError({"sso": _("This school account is linked to another user.")})
        if existing is None and UserIdentity.objects.filter(user=user, provider=provider).exists():
            raise ValidationError({"sso": _("Your account is already linked to another account of this provider.")})
        if existing is not None:
            return existing
        identity = UserIdentity.objects.create(
            user=user, provider=provider, subject=subject, email=email, linked_at=timezone.now().replace(microsecond=0)
        )
        audit(
            "sso.linked",
            user,
            properties={"provider": provider, "email": email, "how": how},
            causer=user,
            log="security",
        )
        return identity


class UnlinkIdentity:
    def __call__(self, user: User, identity: UserIdentity) -> None:
        if identity.user_id != user.pk:
            raise PermissionDenied
        provider = identity.provider
        identity.delete()
        audit("sso.unlinked", user, properties={"provider": provider}, causer=user, log="security")
