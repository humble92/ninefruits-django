"""Account invitations (original ``InvitePerson`` and ``AcceptInvitation``, ADR 0007).

People without an account (e.g. students imported from CSV) get an invitation link by email.
Only the SHA-256 hash of the token is stored; a new invitation ends the earlier open ones.
Accepting creates the account linked to the person; receiving the mail proves the address, so
it is marked verified."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from ninefruits.audit.logger import audit
from ninefruits.person.models import AccountInvitation, Person
from ninefruits.person.notifications import send_account_invitation
from ninefruits.person.settings import StudentRecordSettings
from ninefruits.security.models import User


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class InvitePerson:
    def handle(
        self, person: Person, email: str, invited_by: Any = None, base_url: str | None = None
    ) -> AccountInvitation:
        email = email.strip().lower()
        if User.objects.filter(person_id=person.pk).exists():
            raise ValidationError({"email": _("This person already has an account.")})
        if User.objects.filter(email=email).exists():
            raise ValidationError({"email": _("Another account uses this email.")})

        token = secrets.token_urlsafe(36)
        now = timezone.now().replace(microsecond=0)
        expires_at = now + timedelta(days=StudentRecordSettings.load().invitation_valid_days)

        with transaction.atomic():
            person.invitations.filter(accepted_at__isnull=True).update(expires_at=now, updated_at=now)
            invitation = AccountInvitation.objects.create(
                person=person, email=email, token_hash=hash_token(token), expires_at=expires_at, invited_by=invited_by
            )
            audit("account.invited", person, properties={"email": email}, causer=invited_by)

        path = reverse("person:invitation", kwargs={"token": token})
        url = f"{base_url.rstrip('/')}{path}" if base_url else path
        transaction.on_commit(lambda: send_account_invitation(email, url, expires_at))
        return invitation

    __call__ = handle


class AcceptInvitation:
    @staticmethod
    def find(token: str) -> AccountInvitation | None:
        invitation = AccountInvitation.objects.filter(token_hash=hash_token(token)).first()
        return invitation if invitation is not None and invitation.is_usable() else None

    def handle(self, token: str, password: str) -> User:
        invalid = ValidationError(
            {"token": _("This invitation link is invalid or has expired. Ask the school office for a new one.")}
        )
        invitation = self.find(token)
        if invitation is None:
            raise invalid

        with transaction.atomic():
            if User.objects.filter(Q(email=invitation.email) | Q(person_id=invitation.person_id)).exists():
                raise invalid
            now = timezone.now().replace(microsecond=0)
            user = User.objects.create_user(
                email=invitation.email, password=password, person_id=invitation.person_id, email_verified_at=now
            )
            invitation.accepted_at = now
            invitation.save(update_fields=["accepted_at", "updated_at"])
            audit("account.invitation_accepted", user, properties={"person_id": invitation.person_id}, causer=user)
        return user

    __call__ = handle
