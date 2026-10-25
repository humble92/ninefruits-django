"""Organization enums (original ``App\\Domain\\Organization\\Enums``)."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy


class DegreeLevel(models.TextChoices):
    ASSOCIATE = "associate", _("Associate")
    BACHELOR = "bachelor", _("Bachelor")
    MASTER = "master", _("Master")
    DOCTORATE = "doctorate", _("Doctorate")
    CERTIFICATE = "certificate", _("Certificate")
    NON_DEGREE = "non_degree", _("Non-degree")


class OrgUnitChangeType(models.TextChoices):
    """How an org unit relates to its successor after a reorganization."""

    RENAMED = "renamed", _("Renamed")
    MERGED = "merged", pgettext_lazy("reference", "Merged")
    SPLIT = "split", _("Split")
    MOVED = "moved", _("Moved")
