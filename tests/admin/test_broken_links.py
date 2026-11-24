"""Links on screens lead somewhere: view-only record pages render, lists and app pages the user
go to the dashboard when they are empty for the user, and browsers get the error pages of ninefruits.core.errors."""

from __future__ import annotations

import re

import pytest
from django.test import Client, RequestFactory

from ninefruits.core.targeting import TargetCriteria, TargetCriteriaEncoder
from ninefruits.security.enums import MfaEnforcement, Permission
from ninefruits.security.models import User
from ninefruits.settings.groups.security import SecuritySettings
from tests.factories.facility import RoomFactory
from tests.factories.organization import OrgUnitFactory
from tests.factories.security import UserFactory
from tests.factories.term import TermFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("essential_data")]

NOTHING_TO_SHOW = "No information to show"
NO_PERMISSION = "No permission"


@pytest.fixture(autouse=True)
def _mfa_not_used(essential_data: None) -> None:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def test_view_only_record_pages_render_forms_that_adjust_their_fields() -> None:
    # The forms set querysets/widgets in __init__; Django drops every field of a view-only form.
    viewer = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.REFERENCE_DATA_VIEW])
    client = signed_in(viewer)
    urls = [
        f"/admin/term/term/{TermFactory().pk}/change/",
        f"/admin/facility/room/{RoomFactory().pk}/change/",
        f"/admin/organization/orgunit/{OrgUnitFactory().pk}/change/",
    ]
    for url in urls:
        response = client.get(url)
        assert response.status_code == 200, url
        assert 'name="_save"' not in response.content.decode(), url


def test_a_record_page_the_user_may_not_open_says_so() -> None:
    user = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.REFERENCE_DATA_VIEW])
    other = UserFactory()

    response = signed_in(user).get(f"/admin/security/user/{other.pk}/change/")

    assert response.status_code == 403
    assert NO_PERMISSION in response.content.decode()


def test_lists_the_user_may_not_open_show_the_403_page() -> None:
    user = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])
    response = signed_in(user).get("/admin/security/user/")
    assert response.status_code == 403
    assert NO_PERMISSION in response.content.decode()


def test_a_record_page_does_not_link_to_a_list_the_user_may_not_open() -> None:
    from tests.factories.person import InstructorFactory

    person = InstructorFactory().person  # instructors are visible to everyone, the list is not
    list_link = re.compile(r'href="/admin/person/person/(\?[^"]*)?"')
    user = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])

    response = signed_in(user).get(f"/admin/person/person/{person.pk}/change/")
    assert response.status_code == 200
    assert not list_link.search(response.content.decode())  # neither "Close" nor the header part

    viewer = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.PEOPLE_VIEW])
    assert list_link.search(signed_in(viewer).get(f"/admin/person/person/{person.pk}/change/").content.decode())


def test_an_app_index_without_lists_goes_to_the_dashboard() -> None:
    user = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])
    response = signed_in(user).get("/admin/importing/")
    assert response.status_code == 302
    assert response["Location"] == "/admin/"


def test_browser_pages_show_the_404_and_403_pages_in_the_layout() -> None:
    client = signed_in(UserFactory())

    missing = client.get("/portal/sections/999999/grades/")
    assert missing.status_code == 404
    assert NOTHING_TO_SHOW in missing.content.decode()

    forbidden = client.get("/admin/")  # no admin panel access
    assert forbidden.status_code == 403
    content = forbidden.content.decode()
    assert NO_PERMISSION in content
    assert forbidden["X-Request-Id"] in content  # the reference for support


def test_an_expired_form_shows_the_expired_page() -> None:
    client = Client(enforce_csrf_checks=True)
    response = client.post("/accounts/login/", {"login": "a@example.test", "password": "x"})
    assert response.status_code == 403
    assert "The page has expired" in response.content.decode()


def test_the_400_and_500_pages_render_without_the_layout() -> None:
    from ninefruits.core import errors

    request = RequestFactory().get("/portal/")
    for response, status, title in (
        (errors.bad_request(request), 400, "Bad request"),
        (errors.server_error(request), 500, "Something went wrong"),
    ):
        assert response.status_code == status
        content = response.content.decode()
        assert title in content
        assert "<!DOCTYPE html>" in content
        assert "app.js" not in content  # no built assets


def test_rate_limits_show_the_429_page() -> None:
    from ninefruits.core import errors

    response = errors.too_many_requests(RequestFactory().get("/accounts/login/"))
    assert response.status_code == 429
    assert "Too many requests" in response.content.decode()


def test_api_errors_keep_their_own_responses() -> None:
    response = signed_in(UserFactory()).get("/api/does-not-exist/", HTTP_ACCEPT="application/json")
    assert response.status_code == 404
    assert "<html" not in response.content.decode()


def test_target_criteria_display_as_json() -> None:
    import json

    criteria = TargetCriteria(year_levels=[1, 2])
    assert json.loads(json.dumps(criteria, cls=TargetCriteriaEncoder)) == {"year_levels": [1, 2]}
