"""Person admin screens (original Filament resources of the ``StudentRecords`` navigation
group). Importing registers the model admins and the student record settings page."""

from ninefruits.person import settings_pages  # noqa: F401  (registers the settings page)

from . import instructors, people, requests, student_records  # noqa: F401
