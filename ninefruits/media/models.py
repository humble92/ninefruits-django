"""Files attached to records (original spatie/laravel-medialibrary ``media`` table, unchanged).

The owner is polymorphic: ``model_type`` holds the owner's Django model label in lower case
(``person.person``; ADR 0002-django), ``model_id`` its primary key. Files live on a private
storage under ``<media id>/<file name>`` (spatie's default path) and are served only through
permission checked views (``ninefruits.media.views.PrivateMediaDownloadView``)."""

from __future__ import annotations

import uuid
from datetime import UTC
from typing import Any, Self

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ninefruits.core import morph
from ninefruits.core.models import VisibleQuerySet


class NaiveUtcDateTimeField(models.DateTimeField):  # type: ignore[type-arg]
    """``timestamp(0) without time zone`` (as spatie created it): stored in UTC, read back aware."""

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if value is not None and timezone.is_naive(value):
            return value.replace(tzinfo=UTC)
        return value


class JsonColumnField(models.JSONField):
    """A ``json`` (not ``jsonb``) column: psycopg already decodes it."""

    def from_db_value(self, value: Any, expression: Any, connection: Any) -> Any:
        if isinstance(value, bytes | bytearray):
            value = value.decode()
        if value is None or isinstance(value, str):
            return super().from_db_value(value, expression, connection)
        return value


class MediaQuerySet(VisibleQuerySet):
    def for_owner(self, owner: models.Model, collection: str | None = None) -> Self:
        queryset = self.filter(model_type=morph.morph_type(owner), model_id=owner.pk)
        return queryset.filter(collection_name=collection) if collection is not None else queryset


class Media(models.Model):
    model_type = models.CharField(max_length=255)
    model_id = models.BigIntegerField()
    uuid = models.UUIDField(null=True, blank=True, default=uuid.uuid4)
    collection_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=255, null=True, blank=True)
    disk = models.CharField(max_length=255)
    conversions_disk = models.CharField(max_length=255, null=True, blank=True)
    size = models.BigIntegerField()
    manipulations = JsonColumnField(default=list)
    custom_properties = JsonColumnField(default=dict)
    generated_conversions = JsonColumnField(default=list)
    responsive_images = JsonColumnField(default=list)
    order_column = models.IntegerField(null=True, blank=True)
    created_at = NaiveUtcDateTimeField(null=True, blank=True, default=timezone.now)
    updated_at = NaiveUtcDateTimeField(null=True, blank=True, auto_now=True)

    objects = MediaQuerySet.as_manager()

    class Meta:
        db_table = "media"
        verbose_name = _("file")
        verbose_name_plural = _("files")
        default_permissions = ()
        # Indexes media_model_type_model_id_index and media_order_column_index exist in the
        # database (Django limits declared index names to 30 characters, so they are omitted).
        constraints = [models.UniqueConstraint(fields=["uuid"], name="media_uuid_unique")]

    def __str__(self) -> str:
        return self.file_name

    def __repr__(self) -> str:
        # The file name may contain personal data; keep it out of logs.
        return f"<Media {self.pk} {self.collection_name}>"

    @property
    def path(self) -> str:
        """Path on the storage (spatie DefaultPathGenerator: ``<id>/<file name>``)."""
        return f"{self.pk}/{self.file_name}"

    @property
    def directory(self) -> str:
        return str(self.pk)

    @property
    def sha256(self) -> str | None:
        value = (self.custom_properties or {}).get("sha256") if isinstance(self.custom_properties, dict) else None
        return str(value) if value else None

    @property
    def owner(self) -> models.Model | None:
        try:
            return morph.resolve(self.model_type, self.model_id)
        except LookupError, ValueError:
            return None

    def custom_property(self, name: str, default: Any = None) -> Any:
        properties = self.custom_properties if isinstance(self.custom_properties, dict) else {}
        return properties.get(name, default)

    def belongs_to(self, owner: models.Model) -> bool:
        return self.model_type == morph.morph_type(owner) and int(self.model_id) == int(owner.pk)
