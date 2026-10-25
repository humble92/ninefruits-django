"""Graduation admin screens (original Filament ``Resources/Graduation`` and
``ManageGraduationSettings``)."""

from ninefruits.graduation import settings_pages  # noqa: F401  (registers the settings page)

from .audits import DegreeAuditAdmin
from .student_record import DegreeAuditActionsMixin
from .waivers import DegreeRequirementWaiverAdmin

__all__ = ["DegreeAuditActionsMixin", "DegreeAuditAdmin", "DegreeRequirementWaiverAdmin"]
