"""CSV import runs (original Filament ``imports`` and ``failed_import_rows`` tables).

An ``Import`` is one file imported by one user (the admin screen or ``reference_import
--actor``). ``importer`` holds the import type key (``org_units``, ``rooms`` ...; the original
stored the PHP importer class). Rows that could not be imported are kept in
``FailedImportRow`` with the reason, so they can be downloaded, fixed and imported again."""

from __future__ import annotations

from typing import Any, Self

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import VisibleQuerySet


class ImportQuerySet(VisibleQuerySet):
    def visible_to(self, user: Any) -> Self:
        """Everyone sees their own imports; holders of ``reference_data.import`` see all."""
        from ninefruits.security.enums import Permission

        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()
        if user.has_perm(Permission.REFERENCE_DATA_IMPORT):
            return self
        return self.filter(user_id=user.pk)


class Import(models.Model):
    completed_at = models.DateTimeField(pgettext_lazy("importing", "Completed"), null=True, blank=True)
    file_name = models.CharField(_("File"), max_length=255)
    file_path = models.CharField(max_length=255)
    importer = models.CharField(_("Import type"), max_length=255)
    processed_rows = models.IntegerField(_("Processed rows"), default=0)
    total_rows = models.IntegerField(_("Rows"))
    successful_rows = models.IntegerField(_("Imported rows"), default=0)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="imports", verbose_name=_("Imported by")
    )
    created_at = models.DateTimeField(_("Started"), null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True)

    objects = ImportQuerySet.as_manager()

    class Meta:
        db_table = "imports"
        ordering = ["-created_at", "-id"]
        verbose_name = _("CSV import")
        verbose_name_plural = _("CSV imports")

    def __str__(self) -> str:
        return f"{self.importer} {self.file_name}"

    def __repr__(self) -> str:
        return f"<Import {self.pk} {self.importer}>"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.created_at is None:
            from django.utils import timezone

            self.created_at = timezone.now().replace(microsecond=0)
        super().save(*args, **kwargs)

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    def failed_rows_count(self) -> int:
        return self.failed_rows.count()


class FailedImportRow(models.Model):
    data = models.JSONField(_("Row"))
    import_run = models.ForeignKey(Import, on_delete=models.CASCADE, related_name="failed_rows", db_column="import_id")
    validation_error = models.TextField(_("Error"), null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True, auto_now=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "failed_import_rows"
        ordering = ["id"]
        verbose_name = _("failed row")
        verbose_name_plural = _("failed rows")

    def __str__(self) -> str:
        return str(self.validation_error or "")

    def __repr__(self) -> str:
        # Rows may hold personal data (student imports): never in repr.
        return f"<FailedImportRow {self.pk} import={self.import_run_id}>"
