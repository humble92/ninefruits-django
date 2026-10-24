"""Offering admin screens: sections with their meetings, instructors and seat groups, and the
room and instructor timetables (original Filament ``Resources/Offering`` and ``ViewTimetables``)."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from ninefruits.adminpanel.navigation import NavigationGroup, register_link

from . import sections
from .timetables import can_view_timetables, timetables_view

admin.site.register_view(  # type: ignore[attr-defined]
    "offering/timetables/", timetables_view, name="offering_timetables"
)
register_link(
    group=NavigationGroup.CURRICULUM,
    label=_("Timetables"),
    url_name="admin:offering_timetables",
    permission=can_view_timetables,
    icon="calendar_month",
    order=40,
)

__all__ = ["sections"]
