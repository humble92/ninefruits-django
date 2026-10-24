"""Invitation for a person without an account (original ``AccountInvitation``). Only the
SHA-256 hash of the token is stored; a new invitation makes the earlier ones unusable."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet


class AccountInvitation(TimeStampedModel):
    person = models.ForeignKey("person.Person", on_delete=models.CASCADE, related_name="invitations")
    email = models.CharField(_("Sign-in email"), max_length=255)
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "account_invitations"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"invitation {self.pk}"

    def __repr__(self) -> str:
        return f"<AccountInvitation {self.pk} person={self.person_id}>"

    def is_usable(self) -> bool:
        return self.accepted_at is None and self.expires_at > timezone.now()
