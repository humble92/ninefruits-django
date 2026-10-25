"""Audit tables (ADR 0002): ``audit.activity_log`` (business audit, original spatie Activity),
``audit.record_changes`` (written by the ``audit.record_change()`` trigger only) and
``audit.security_events`` (security log).

The tables live in the ``audit`` schema and are created by the replayed DDL, so the models are
unmanaged and use the quoting trick ``db_table = 'audit"."activity_log'`` (porting-plan 5.3,
pinned by tests/audit/test_audit_models.py). The runtime role may only INSERT and SELECT
``activity_log`` and ``security_events`` and only SELECT ``record_changes``; the
``*_before_change_prevent_modification`` triggers block UPDATE, DELETE and TRUNCATE for
everyone, including the schema owner. ``row_hash`` is set by an INSERT trigger and
``chain_hash``/``sealed_at`` by ``audit.seal()`` (see ninefruits.audit.chain)."""

from __future__ import annotations

from typing import Any, Self

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.audit.security_events import SecurityEventType
from ninefruits.core import morph
from ninefruits.core.models import VisibleQuerySet
from ninefruits.security.enums import Permission


class AppendOnlyError(RuntimeError):
    """Raised before the database would refuse a change to an audit record."""


class AuditQuerySet(VisibleQuerySet):
    """Audit records are visible as a whole to holders of the viewing permission (original
    AuditRecordPolicy / SecurityEventPolicy); nobody else sees any."""

    permission: str = Permission.AUDIT_RECORDS_VIEW

    def visible_to(self, user: Any) -> Self:
        if user is not None and getattr(user, "is_authenticated", False) and user.has_perm(str(self.permission)):
            return self
        return self.none()


class SecurityEventQuerySet(AuditQuerySet):
    permission = Permission.SECURITY_EVENTS_VIEW


class AuditRecord(models.Model):
    """Common behaviour: append only, morph helpers and the hash chain columns."""

    row_hash = models.CharField(max_length=64, null=True, blank=True, editable=False)
    chain_hash = models.CharField(max_length=64, null=True, blank=True, editable=False)
    sealed_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        abstract = True

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self._state.adding:
            raise AppendOnlyError(f"Audit records are append-only: {self._meta.db_table}")
        kwargs["force_insert"] = True
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        raise AppendOnlyError(f"Audit records are append-only: {self._meta.db_table}")

    @staticmethod
    def describe_morph(type_name: str | None, pk: Any) -> str | None:
        """``Person #12`` for display. Accepts Django labels (``person.person``) and the original
        PHP class names (``App\\Models\\Person\\Person``) of restored data."""
        if not type_name:
            return None
        if "\\" in type_name:
            name = type_name.rsplit("\\", 1)[-1]
        else:
            try:
                from django.apps import apps

                name = apps.get_model(type_name).__name__
            except LookupError, ValueError:
                name = type_name.rsplit(".", 1)[-1]
        return f"{name} #{pk}" if pk is not None else name


class ActivityLog(AuditRecord):
    """Business audit record: who did what, to which record, why, with the request context
    (original ``App\\Models\\Security\\Activity`` on spatie/laravel-activitylog). Written by
    ``ninefruits.audit.logger.audit()``."""

    log_name = models.CharField(_("Log"), max_length=255, null=True, blank=True)
    description = models.TextField()
    subject_type = models.CharField(max_length=255, null=True, blank=True)
    subject_id = models.BigIntegerField(null=True, blank=True)
    event = models.CharField(_("Event"), max_length=255, null=True, blank=True)
    causer_type = models.CharField(max_length=255, null=True, blank=True)
    causer_id = models.BigIntegerField(null=True, blank=True)
    attribute_changes = models.JSONField(null=True, blank=True)
    properties = models.JSONField(_("Details"), null=True, blank=True)
    reason = models.TextField(_("Reason"), null=True, blank=True)
    request_id = models.CharField(pgettext_lazy("admin", "Request ID"), max_length=255, null=True, blank=True)
    ip_address = models.CharField(_("IP address"), max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(pgettext_lazy("admin", "Time"), null=True, blank=True, default=timezone.now)
    updated_at = models.DateTimeField(null=True, blank=True, default=timezone.now)

    objects = AuditQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = 'audit"."activity_log'
        verbose_name = _("activity")
        verbose_name_plural = _("activity log")
        default_permissions = ()

    def __str__(self) -> str:
        return self.event or self.description

    def __repr__(self) -> str:
        return f"<ActivityLog {self.pk} {self.event}>"

    @property
    def subject(self) -> models.Model | None:
        return morph.resolve(self.subject_type, self.subject_id)

    @property
    def causer(self) -> models.Model | None:
        return morph.resolve(self.causer_type, self.causer_id)

    @property
    def subject_display(self) -> str | None:
        return self.describe_morph(self.subject_type, self.subject_id)


class RecordChange(AuditRecord):
    """Row written by the ``audit.record_change()`` trigger. Read only."""

    OPERATIONS = (("INSERT", "INSERT"), ("UPDATE", "UPDATE"), ("DELETE", "DELETE"), ("TRUNCATE", "TRUNCATE"))

    occurred_at = models.DateTimeField(pgettext_lazy("admin", "Time"), default=timezone.now)
    transaction_id = models.BigIntegerField(_("Transaction"))
    table_schema = models.CharField(max_length=255)
    table_name = models.CharField(_("Table"), max_length=255)
    operation = models.CharField(pgettext_lazy("admin", "Operation"), max_length=16, choices=OPERATIONS)
    record_id = models.CharField(_("Record ID"), max_length=255, null=True, blank=True)
    old_values = models.JSONField(_("Before"), null=True, blank=True)
    new_values = models.JSONField(_("After"), null=True, blank=True)
    changed_columns = models.JSONField(_("Changed columns"), null=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        null=True,
        blank=True,
        related_name="+",
    )
    actor = models.CharField(_("User"), max_length=255, null=True, blank=True)
    request_id = models.CharField(pgettext_lazy("admin", "Request ID"), max_length=255, null=True, blank=True)
    database_user = models.CharField(_("Database user"), max_length=255)

    objects = AuditQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = 'audit"."record_changes'
        verbose_name = _("data change")
        verbose_name_plural = _("data changes")
        default_permissions = ()

    def __str__(self) -> str:
        return f"{self.operation} {self.table_name} {self.record_id or ''}".strip()

    def __repr__(self) -> str:
        return f"<RecordChange {self.pk} {self.operation} {self.table_name}>"

    def save(self, *args: Any, **kwargs: Any) -> None:
        raise AppendOnlyError("audit.record_changes is written by the audit trigger only")

    def diff(self) -> list[tuple[str, Any, Any]]:
        """``(column, before, after)`` for display: the changed columns of an UPDATE, every
        column of an INSERT or DELETE."""
        old = self.old_values or {}
        new = self.new_values or {}
        columns = list(self.changed_columns or []) or sorted(set(old) | set(new))
        return [(column, old.get(column), new.get(column)) for column in columns]


class SecurityEvent(AuditRecord):
    """Security log entry (original ``App\\Models\\Security\\SecurityEvent``). Written by
    ``ninefruits.audit.security_events.record_security_event()``."""

    occurred_at = models.DateTimeField(pgettext_lazy("admin", "Time"), default=timezone.now)
    type = models.CharField(
        _("Event"),
        max_length=255,
        choices=[(event_type.value, event_type.label) for event_type in SecurityEventType],
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        null=True,
        blank=True,
        related_name="+",
    )
    identifier = models.CharField(_("Sign-in name"), max_length=255, null=True, blank=True)
    subject_type = models.CharField(max_length=255, null=True, blank=True)
    subject_id = models.BigIntegerField(null=True, blank=True)
    properties = models.JSONField(_("Details"), null=True, blank=True)
    request_id = models.CharField(pgettext_lazy("admin", "Request ID"), max_length=255, null=True, blank=True)
    ip_address = models.CharField(_("IP address"), max_length=45, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)

    objects = SecurityEventQuerySet.as_manager()

    class Meta:
        managed = False
        db_table = 'audit"."security_events'
        verbose_name = _("security event")
        verbose_name_plural = _("security events")
        default_permissions = ()

    def __str__(self) -> str:
        return str(self.event_type.label) if self.event_type else self.type

    def __repr__(self) -> str:
        return f"<SecurityEvent {self.pk} {self.type}>"

    @property
    def event_type(self) -> SecurityEventType | None:
        try:
            return SecurityEventType(self.type)
        except ValueError:
            return None

    @property
    def subject(self) -> models.Model | None:
        return morph.resolve(self.subject_type, self.subject_id)

    @property
    def subject_display(self) -> str | None:
        return self.describe_morph(self.subject_type, self.subject_id)
