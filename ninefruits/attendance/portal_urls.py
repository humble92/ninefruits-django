"""Portal routes of attendance, included in ``ninefruits.portal.urls`` (names ``portal:...``)."""

from __future__ import annotations

from django.urls import path

from ninefruits.attendance.views.portal import MyAttendanceView, SectionAttendanceView

urlpatterns = [
    path("sections/<int:pk>/attendance/", SectionAttendanceView.as_view(), name="attendance_section"),
    path("attendance/", MyAttendanceView.as_view(), name="attendance"),
]
