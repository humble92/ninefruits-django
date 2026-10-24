"""Grading admin screens (navigation group "Grades") and the grade scales (reference data)."""

from ninefruits.grading import settings_pages  # noqa: F401  (registers the settings page)

from . import grade_changes, grade_scales, method_requests, section_grades, term_records  # noqa: F401
