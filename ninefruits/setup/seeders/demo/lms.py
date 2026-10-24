"""Demo LMS (original ``DemoLmsSeeder``): a ``null`` platform ``DEMO`` (records, no calls) with
the first 20 published sections of the current term linked through ``SyncSection``, so the course
links, the sync log and the portal course links can be seen. The members synchronized are the
instructors and students who have an account in the demo. Nothing happens when a platform exists
already or there is no current term."""

from __future__ import annotations

from django.utils import timezone

from ninefruits.setup.seeders.base import Seeder

SECTIONS = 20


class DemoLmsSeeder(Seeder):
    def run(self) -> None:
        from ninefruits.lms.actions import SyncSection
        from ninefruits.lms.models import LmsPlatform
        from ninefruits.offering.enums import SectionStatus
        from ninefruits.offering.models import Section
        from ninefruits.term.enums import TermStatus
        from ninefruits.term.models import Term

        today = timezone.localdate()
        current = (
            Term.objects.filter(status=TermStatus.PUBLISHED, start_date__lte=today).order_by("-start_date").first()
        )
        if current is None or LmsPlatform.objects.exists():
            return

        platform = LmsPlatform.objects.create(
            code="DEMO",
            name={"en": "Demo LMS", "ko": "시연용 LMS", "zh-hans": "演示 LMS", "lo": "LMS ສຳລັບສາທິດ"},
            driver="null",
            base_url="https://lms.example.test",
            options={},
            is_active=True,
            should_sync_enrollments=True,
            should_pull_grades=False,
        )
        sync = SyncSection()
        sections = Section.objects.filter(term_id=current.pk, status=SectionStatus.PUBLISHED).select_related("course")
        for section in sections.order_by("pk")[:SECTIONS]:
            sync.handle(platform, section)
