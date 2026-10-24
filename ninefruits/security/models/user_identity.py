"""External sign-in identity of an account, e.g. the school's OIDC account (original
``App\\Models\\Security\\UserIdentity``)."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from ninefruits.core.models import VisibleQuerySet


class UserIdentity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="identities")
    provider = models.CharField(max_length=64)
    subject = models.CharField(max_length=255)
    email = models.CharField(max_length=255, null=True, blank=True)
    linked_at = models.DateTimeField(default=timezone.now)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True, default=timezone.now, editable=False)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True, editable=False)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "user_identities"
        constraints = [
            models.UniqueConstraint(fields=["provider", "subject"], name="user_identities_provider_subject_unique"),
            models.UniqueConstraint(fields=["user", "provider"], name="user_identities_user_id_provider_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.provider}"

    def __repr__(self) -> str:
        return f"<UserIdentity {self.pk} user={self.user_id} provider={self.provider}>"
