"""Reporting admin screens: the standard reports page (original Filament page ``Reports``)."""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from ninefruits.adminpanel.navigation import NavigationGroup
from ninefruits.security.enums import Permission

from .reports import reports_view

admin.site.register_view(  # type: ignore[attr-defined]
    "reports/",
    reports_view,
    name="reports",
    permission=Permission.REPORTS_VIEW,
    navigation_group=NavigationGroup.REPORTS,
    label=_("Reports"),
    icon="table_rows",
    order=10,
)

__all__ = ["reports_view"]
