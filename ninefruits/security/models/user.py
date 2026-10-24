from __future__ import annotations

from typing import Any

from django.contrib.auth import get_backends
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> User:
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser):
    """Account (original ``users`` table, unchanged). The Fortify two-factor columns
    (``two_factor_secret``, ``two_factor_recovery_codes``, ``two_factor_confirmed_at``) and
    ``remember_token`` are kept for schema equality but unused: TOTP and recovery codes live in
    allauth's ``mfa_authenticator`` table (ADR 0002-django)."""

    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.CharField(max_length=255, unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    password = models.CharField(max_length=255)
    two_factor_secret = models.TextField(null=True, blank=True, editable=False)
    two_factor_recovery_codes = models.TextField(null=True, blank=True, editable=False)
    two_factor_confirmed_at = models.DateTimeField(null=True, blank=True, editable=False)
    email_mfa_enabled_at = models.DateTimeField(null=True, blank=True)
    mfa_grace_started_at = models.DateTimeField(null=True, blank=True)
    locale = models.CharField(max_length=20, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True, db_column="last_login_at")
    remember_token = models.CharField(max_length=100, null=True, blank=True, editable=False)
    created_at = models.DateTimeField(null=True, blank=True, default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True)
    # Replaced by a OneToOneField to person.Person in Phase 2.
    person_id = models.BigIntegerField(null=True, blank=True, unique=True)
    failed_login_count = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return self.name or self.email

    def __repr__(self) -> str:
        # Never include secrets or personal data (original Phase 13 H1).
        return f"<User {self.pk}>"

    # -- account state (original App\\Models\\User) --------------------------------------------
    @property
    def last_login_at(self) -> Any:
        return self.last_login

    def display_name(self) -> str:
        """The person's name when linked (Phase 2), otherwise the account's own name."""
        if self.person_id is not None:
            person = getattr(self, "person", None)
            if person is not None and hasattr(person, "display_name"):
                return str(person.display_name())
        return self.name or self.email

    def is_locked(self) -> bool:
        return self.locked_until is not None and self.locked_until > timezone.now()

    def has_verified_email(self) -> bool:
        return self.email_verified_at is not None

    def get_full_name(self) -> str:
        return self.display_name()

    def get_short_name(self) -> str:
        return self.display_name()

    def preferred_locale(self) -> str | None:
        return self.locale

    # -- authorization (CatalogPermissionBackend answers; no PermissionsMixin) ------------------
    def has_perm(self, perm: str, obj: object | None = None) -> bool:
        if not self.is_active:
            return False
        return any(hasattr(backend, "has_perm") and backend.has_perm(self, perm, obj) for backend in get_backends())

    def has_perms(self, perm_list: list[str], obj: object | None = None) -> bool:
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label: str) -> bool:
        return self.is_active and self.is_staff

    @property
    def is_staff(self) -> bool:
        """May open the admin panel (any admin permission; see security.authorization)."""
        from ninefruits.security.authorization import can_access_admin

        return can_access_admin(self)

    @property
    def is_superuser(self) -> bool:
        return False
