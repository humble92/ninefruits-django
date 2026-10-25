"""One enrollment added to or removed from the platform course (original ``SyncEnrollment``). A
section not yet linked is synchronized whole first."""

from __future__ import annotations

from typing import Any

from ninefruits.lms.enums import STUDENT, LinkStatus
from ninefruits.lms.models import LmsCourseLink, LmsPlatform

from .sync_section import SyncSection, account_of


class SyncEnrollment:
    def __init__(self, sections: SyncSection | None = None) -> None:
        self.sections = sections or SyncSection()

    def added(self, platform: LmsPlatform, enrollment: Any) -> None:
        link = LmsCourseLink.objects.filter(platform=platform, section_id=enrollment.section_id).first()
        if link is None or link.status != LinkStatus.LINKED:
            self.sections.handle(platform, enrollment.section)
            return
        user = account_of(enrollment.student_record.person)
        if user is not None and platform.should_sync_enrollments:
            self.sections.member(platform, link, user, STUDENT, enrollment)

    def removed(self, platform: LmsPlatform, enrollment: Any) -> None:
        link = LmsCourseLink.objects.filter(platform=platform, section_id=enrollment.section_id).first()
        user = account_of(enrollment.student_record.person)
        if link is not None and user is not None and platform.should_sync_enrollments:
            self.sections.remove_member(platform, link, user, enrollment)
