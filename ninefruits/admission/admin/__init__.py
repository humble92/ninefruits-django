"""Admission admin screens (original Filament resources of the ``Admissions`` navigation group).
Importing registers the model admins and the admission settings page."""

from ninefruits.admission import settings_pages  # noqa: F401  (registers the settings page)

from . import applications, cycles  # noqa: F401
