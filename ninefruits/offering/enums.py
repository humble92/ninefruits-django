"""Offering enums (original ``App\\Domain\\Offering\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class SectionStatus(models.TextChoices):
    """draft: being planned, visible to staff only. published: in the course catalog (and
    registration). cancelled: kept for history; its meetings free their rooms and instructors."""

    DRAFT = "draft", pgettext_lazy("offering", "Draft")
    PUBLISHED = "published", pgettext_lazy("offering.section_statuses", "Published")
    CANCELLED = "cancelled", pgettext_lazy("offering", "Cancelled")


class InstructorRole(models.TextChoices):
    PRIMARY = "primary", pgettext_lazy("offering", "Instructor")
    CO_INSTRUCTOR = "co_instructor", _("Co-instructor")
    ASSISTANT = "assistant", _("Teaching assistant")
