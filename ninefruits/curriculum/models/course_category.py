"""Course category (original ``App\\Models\\Curriculum\\CourseCategory``), e.g. general education
required, major elective (legacy SFOBJDIST)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from ninefruits.core.models import TimeStampedModel, VisibleQuerySet
from ninefruits.i18n.fields import TranslatableJSONField


class CourseCategory(TimeStampedModel):
    code = models.CharField(pgettext_lazy("reference", "Code"), max_length=32, unique=True)
    name = TranslatableJSONField(pgettext_lazy("reference", "Name"))
    parent = models.ForeignKey(
        "self", on_delete=models.RESTRICT, null=True, blank=True, related_name="children", verbose_name=_("Parent")
    )
    sort_order = models.IntegerField(_("Order"), default=0)
    is_active = models.BooleanField(pgettext_lazy("reference.fields", "Active"), default=True)

    objects = VisibleQuerySet.as_manager()

    class Meta:
        db_table = "course_categories"
        ordering = ["sort_order", "code"]
        verbose_name = _("course category")
        verbose_name_plural = _("course categories")

    def __str__(self) -> str:
        return f"{self.code} {self.name or ''}".strip()
