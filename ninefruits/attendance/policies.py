"""Attendance policies (ADR 0015). Meetings and records change only through the actions
(``ManageClassMeetings``, ``RecordAttendance``), which check the section's instructors and
``sections.manage`` staff; these policies answer the admin's view questions. Registered from
``AttendanceConfig.ready``."""

from __future__ import annotations

from typing import Any

from ninefruits.security.enums import Permission
from ninefruits.security.policies import Policy, register


class _ThroughActions(Policy):
    def create(self, user: Any, obj: Any) -> bool:
        return False

    def update(self, user: Any, obj: Any) -> bool:
        return False

    def delete(self, user: Any, obj: Any) -> bool:
        return False


class ClassMeetingPolicy(_ThroughActions):
    """Schedule information: staff who see sections list them; anyone signed in reads one."""

    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.SECTIONS_VIEW) or user.has_perm(Permission.SECTIONS_MANAGE))

    def view(self, user: Any, obj: Any) -> bool:
        return bool(getattr(user, "is_authenticated", False))

    def manage(self, user: Any, obj: Any) -> bool:
        """Generate, add, cancel and restore: the section's instructors and ``sections.manage``
        staff covering it."""
        from ninefruits.attendance.actions import ManageClassMeetings

        return obj is not None and ManageClassMeetings.can_manage(obj.section, user)


class AttendanceRecordPolicy(_ThroughActions):
    def view_any(self, user: Any, obj: Any) -> bool:
        return bool(user.has_perm(Permission.SECTIONS_VIEW) or user.has_perm(Permission.SECTIONS_MANAGE))

    def view(self, user: Any, obj: Any) -> bool:
        from ninefruits.attendance.models import AttendanceRecord

        return obj is not None and AttendanceRecord.objects.visible_to(user).filter(pk=obj.pk).exists()


def register_policies() -> None:
    register("attendance.classmeeting", ClassMeetingPolicy())
    register("attendance.attendancerecord", AttendanceRecordPolicy())
