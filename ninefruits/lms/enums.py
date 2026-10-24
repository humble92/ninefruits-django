"""LMS enums (original ``App\\Domain\\Lms\\Enums``, ADR 0017)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class LinkStatus(models.TextChoices):
    PENDING = "pending", pgettext_lazy("lms", "Pending")
    LINKED = "linked", _("Linked")
    FAILED = "failed", pgettext_lazy("lms", "Failed")


class LmsDriver(models.TextChoices):
    """Which connector talks to the platform. Only ``null`` (records, no calls) ships; the others
    are named so platforms can be prepared (``ConnectorRegistry`` fails them loudly)."""

    NULL = "null", _("None (records only)")
    MOODLE = "moodle", "Moodle"
    OPENEDX = "openedx", "Open edX"


class SyncOperation(models.TextChoices):
    COURSE_SYNC = "course.sync", pgettext_lazy("lms", "Course")
    ENROLLMENT_ADD = "enrollment.add", _("Add member")
    ENROLLMENT_REMOVE = "enrollment.remove", _("Remove member")
    GRADES_PULL = "grades.pull", _("Pull scores")
    #: Final scores the platform delivered through the API (``POST .../scores/``); the grade
    #: entry import reads the latest delivery when the connector reports none.
    GRADES_DELIVERED = "grades.delivered", _("Scores delivered")
    RECONCILE = "reconcile", _("Reconcile")


class SyncStatus(models.TextChoices):
    QUEUED = "queued", _("Queued")
    SUCCEEDED = "succeeded", _("Succeeded")
    FAILED = "failed", pgettext_lazy("lms", "Failed")
    SKIPPED = "skipped", _("Skipped")


#: Roles of a member on the platform course.
INSTRUCTOR = "instructor"
STUDENT = "student"
