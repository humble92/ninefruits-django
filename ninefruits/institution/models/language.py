"""ISO 639-1 language (original ``App\\Models\\Institution\\Language``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField


class Language(TimeStampedModel):
    code = models.CharField(_("ISO code"), max_length=3, unique=True)
    alpha3_code = models.CharField(_("Three-letter code"), max_length=3, null=True, blank=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "languages"
        ordering = ["code"]
        verbose_name = _("language")
        verbose_name_plural = _("languages")

    def __str__(self) -> str:
        return str(self.name or self.code)
