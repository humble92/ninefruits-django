"""LMS integration base (original ``App\\Models\\Lms\\*``, ADR 0017).

- :class:`LmsPlatform`: an LMS the institution connects to: the driver (connector), the endpoint,
  the encrypted credentials, the options and what is synchronized. Configuration (no row level
  security; the credentials are never shown back).
- :class:`LmsCourseLink`: a section's course on a platform. Anyone signed in reads them (the
  portal shows the course link); writes need ``lms.manage`` or the system context.
- :class:`LmsUserLink`: a user's account on a platform. The user reads their own.
- :class:`LmsSyncLog`: one synchronization step and its outcome (``lms.manage``).

The tables, constraints, audit triggers (credentials as a secret column) and policies
(``db/sql/policies/lms.sql``) come from the replayed DDL (``core/0047``)."""

from __future__ import annotations

from typing import Any, Self

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField
from ninefruits.lms.enums import LinkStatus, LmsDriver, SyncOperation, SyncStatus
from ninefruits.lms.fields import EncryptedJSONField
from ninefruits.security.enums import Permission


def _signed_in(user: Any) -> bool:
    return user is not None and bool(getattr(user, "is_authenticated", False))


def _manages(user: Any) -> bool:
    return _signed_in(user) and bool(user.has_perm(Permission.LMS_MANAGE))


class LmsPlatformQuerySet(VisibleQuerySet):
    def active(self) -> Self:
        return self.filter(is_active=True)

    def visible_to(self, user: Any) -> Self:
        """Configuration: the screens that list platforms need ``lms.manage`` (no RLS)."""
        return self if _manages(user) else self.none()


class LmsPlatform(TimeStampedModel):
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=32, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    #: null (records only), moodle, openedx, ...: the connector that talks to the platform.
    driver = models.CharField(_("Driver"), max_length=32, choices=LmsDriver.choices, default=LmsDriver.NULL)
    base_url = models.CharField(_("Base URL"), max_length=255, null=True, blank=True)
    #: Tokens and secrets, encrypted at rest; never shown back.
    credentials = EncryptedJSONField(_("Credentials"))
    options = models.JSONField(_("Options"), default=dict, blank=True)
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=False)
    should_sync_enrollments = models.BooleanField(_("Synchronize rosters"), default=True)
    should_pull_grades = models.BooleanField(_("Pull final scores"), default=False)

    objects = LmsPlatformQuerySet.as_manager()

    class Meta:
        db_table = "lms_platforms"
        ordering = ["code"]
        verbose_name = _("LMS platform")
        verbose_name_plural = _("LMS platforms")

    def __str__(self) -> str:
        return str(self.name or self.code)

    def __repr__(self) -> str:
        return f"<LmsPlatform {self.pk} {self.code} {self.driver}>"

    def credential(self, key: str, default: str | None = None) -> str | None:
        """One credential value for a connector (``platform.credential("token")``)."""
        return (self.credentials or {}).get(key, default)


class LmsCourseLinkQuerySet(VisibleQuerySet):
    def linked(self) -> Self:
        return self.filter(status=LinkStatus.LINKED)

    def visible_to(self, user: Any) -> Self:
        """Anyone signed in (RLS ``lms_course_links_select``: the portal course link)."""
        return self if _signed_in(user) else self.none()


class LmsCourseLink(TimeStampedModel):
    platform = models.ForeignKey(
        LmsPlatform,
        on_delete=models.CASCADE,
        related_name="course_links",
        db_column="lms_platform_id",
        verbose_name=_("LMS platform"),
    )
    section = models.ForeignKey(
        "offering.Section",
        on_delete=models.CASCADE,
        related_name="lms_course_links",
        verbose_name=pgettext_lazy("offering", "Section"),
    )
    external_course_id = models.CharField(_("Course id on the platform"), max_length=128, null=True, blank=True)
    external_url = models.CharField(_("Course URL"), max_length=512, null=True, blank=True)
    status = models.CharField(
        pgettext_lazy("registration", "Status"), max_length=16, choices=LinkStatus.choices, default=LinkStatus.PENDING
    )
    last_synced_at = models.DateTimeField(_("Last synced"), null=True, blank=True)
    last_error = models.TextField(_("Last error"), null=True, blank=True)

    objects = LmsCourseLinkQuerySet.as_manager()

    class Meta:
        db_table = "lms_course_links"
        ordering = ["-last_synced_at", "id"]
        verbose_name = _("Course link")
        verbose_name_plural = _("Course links")
        constraints = [
            models.UniqueConstraint(
                fields=["platform", "section"], name="lms_course_links_lms_platform_id_section_id_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.platform_id}:{self.section_id} {self.external_course_id or '-'}"

    @property
    def lms_platform_id(self) -> int:
        return self.platform_id

    @property
    def is_linked(self) -> bool:
        return self.status == LinkStatus.LINKED


class LmsUserLinkQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Users see their own (RLS ``lms_user_links_owner_select``); ``lms.manage`` all."""
        if not _signed_in(user):
            return self.none()
        if _manages(user):
            return self
        return self.filter(user_id=user.pk)


class LmsUserLink(TimeStampedModel):
    platform = models.ForeignKey(
        LmsPlatform,
        on_delete=models.CASCADE,
        related_name="user_links",
        db_column="lms_platform_id",
        verbose_name=_("LMS platform"),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lms_links")
    external_user_id = models.CharField(_("User id on the platform"), max_length=128)
    last_synced_at = models.DateTimeField(_("Last synced"), null=True, blank=True)

    objects = LmsUserLinkQuerySet.as_manager()

    class Meta:
        db_table = "lms_user_links"
        ordering = ["id"]
        verbose_name = _("User link")
        verbose_name_plural = _("User links")
        constraints = [
            models.UniqueConstraint(fields=["platform", "user"], name="lms_user_links_lms_platform_id_user_id_unique"),
            models.UniqueConstraint(
                fields=["platform", "external_user_id"],
                name="lms_user_links_lms_platform_id_external_user_id_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.platform_id}:{self.user_id} {self.external_user_id}"


class LmsSyncLogQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """``lms.manage`` only (RLS ``lms_sync_logs_manage``)."""
        return self if _manages(user) else self.none()


class LmsSyncLog(TimeStampedModel):
    platform = models.ForeignKey(
        LmsPlatform,
        on_delete=models.CASCADE,
        related_name="sync_logs",
        db_column="lms_platform_id",
        verbose_name=_("LMS platform"),
    )
    section = models.ForeignKey(
        "offering.Section",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=pgettext_lazy("offering", "Section"),
    )
    enrollment = models.ForeignKey(
        "registration.Enrollment", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    operation = models.CharField(_("Operation"), max_length=32, choices=SyncOperation.choices)
    status = models.CharField(pgettext_lazy("registration", "Status"), max_length=16, choices=SyncStatus.choices)
    message = models.TextField(_("Message"), null=True, blank=True)
    payload = models.JSONField(null=True, blank=True)
    started_at = models.DateTimeField(_("Started"))
    finished_at = models.DateTimeField(_("Finished"), null=True, blank=True)

    objects = LmsSyncLogQuerySet.as_manager()

    class Meta:
        db_table = "lms_sync_logs"
        ordering = ["-started_at", "-id"]
        verbose_name = _("Sync log")
        verbose_name_plural = _("Sync logs")

    def __str__(self) -> str:
        return f"{self.operation} {self.status}"


__all__ = ["LmsCourseLink", "LmsPlatform", "LmsSyncLog", "LmsUserLink"]
