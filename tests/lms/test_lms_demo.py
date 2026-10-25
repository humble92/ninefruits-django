"""The demo LMS (original ``DemoLmsSeeder``) on the tiny demo: the ``DEMO`` null platform with the
current term's published sections linked (at most 20), every step logged without failures, the
LMS screens for the demo academic affairs account in Korean, and the portal course link of the
demo instructor."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from django.test import Client

from ninefruits.core.db import session_context
from ninefruits.lms.enums import LinkStatus, SyncStatus
from ninefruits.lms.models import LmsCourseLink, LmsPlatform, LmsSyncLog, LmsUserLink
from ninefruits.security.models import User
from ninefruits.setup import conf
from ninefruits.setup.seeders.demo import DemoOptions, use_options
from ninefruits.setup.seeders.demo.accounts import DemoAccountSeeder
from ninefruits.setup.seeders.demo.curriculum import DemoCurriculumSeeder
from ninefruits.setup.seeders.demo.lms import DemoLmsSeeder
from ninefruits.setup.seeders.demo.people import DemoPeopleSeeder
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from ninefruits.setup.seeders.demo.registration import DemoRegistrationSeeder

from .conftest import signed_in

pytestmark = pytest.mark.django_db


@pytest.fixture
def demo(essential_data: None) -> Iterator[None]:
    with use_options(DemoOptions(size="tiny", seed=42)):
        for seeder in (
            DemoAccountSeeder,
            DemoReferenceSeeder,
            DemoPeopleSeeder,
            DemoCurriculumSeeder,
            DemoRegistrationSeeder,
            DemoLmsSeeder,
        ):
            seeder()()
    yield


def test_seeds_the_demo_platform_and_links_and_renders_the_lms_screens(demo: None) -> None:
    platform = LmsPlatform.objects.get(code="DEMO")
    assert platform.driver == "null" and platform.is_active and platform.name_translations["ko"] == "시연용 LMS"
    links = LmsCourseLink.objects.filter(platform=platform)
    assert 0 < links.count() <= 20
    assert set(links.values_list("status", flat=True)) == {LinkStatus.LINKED}
    assert not LmsSyncLog.objects.filter(status=SyncStatus.FAILED).exists()
    assert LmsUserLink.objects.filter(platform=platform).exists()

    # Running again does nothing.
    count = LmsSyncLog.objects.count()
    DemoLmsSeeder()()
    assert LmsSyncLog.objects.count() == count

    staff = User.objects.get(email=f"academic-affairs@{conf.DEMO_EMAIL_DOMAIN}")
    client = Client(headers={"accept-language": "ko"})
    client.force_login(staff)
    session_context().reset()
    for url, text in (
        ("/admin/lms/lmsplatform/", "시연용 LMS"),
        ("/admin/lms/lmscourselink/", "연결됨"),
        ("/admin/lms/lmssynclog/", "성공"),
        (f"/admin/lms/lmsplatform/{platform.pk}/change/", "인증 정보"),
    ):
        response = client.get(url)
        assert response.status_code == 200, url
        assert text in response.content.decode(), url

    instructor = User.objects.get(email=f"instructor@{conf.DEMO_EMAIL_DOMAIN}")
    taught = links.filter(section__instructor_assignments__instructor__person_id=instructor.person_id).first()
    if taught is not None:
        page = signed_in(instructor).get(f"/portal/sections/{taught.section_id}/")
        assert taught.external_url in page.content.decode()
