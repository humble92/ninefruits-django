"""LMS admin screens (original Filament ``Resources/Lms``): platforms, course links, sync logs."""

from .course_links import LmsCourseLinkAdmin
from .platforms import LmsPlatformAdmin
from .sync_logs import LmsSyncLogAdmin

__all__ = ["LmsCourseLinkAdmin", "LmsPlatformAdmin", "LmsSyncLogAdmin"]
