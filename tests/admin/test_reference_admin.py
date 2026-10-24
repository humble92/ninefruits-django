"""Reference data admin screens (original tests/Feature/Admin/ReferenceAdminTest.php and the
reference data datasets of tests/Feature/Admin/AdminPagesTest.php)."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from datetime import date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from ninefruits.facility.models import Building
from ninefruits.importing.models import Import
from ninefruits.institution.models import Country, LookupType
from ninefruits.organization.models import OrgUnit, OrgUnitType
from ninefruits.security.enums import MfaEnforcement, Permission, ScopeType
from ninefruits.security.models import Role, User
from ninefruits.settings.groups.security import SecuritySettings
from ninefruits.setup.seeders.demo.reference import DemoReferenceSeeder
from ninefruits.term.enums import TermStatus, TermWindowType
from ninefruits.term.models import Term, TimeSlot
from tests.factories.facility import BuildingFactory, RoomFactory
from tests.factories.grading import GradeScaleFactory
from tests.factories.organization import OrgUnitFactory
from tests.factories.security import RoleFactory, UserFactory
from tests.factories.term import TermFactory

pytestmark = [pytest.mark.django_db, pytest.mark.usefixtures("essential_data")]


@pytest.fixture(autouse=True)
def _mfa_not_used(essential_data: None) -> None:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


@pytest.fixture
def manager() -> User:
    return UserFactory(permissions=list(Permission))


def signed_in(user: User) -> Client:
    client = Client()
    client.force_login(user)
    return client


def term_form(term: Term, windows: list[dict[str, str]] | None = None, **fields: str) -> dict[str, str]:
    """POST data of the term change form with new window forms."""
    data = {
        "academic_year": str(term.academic_year_id),
        "term_type": str(term.term_type_id),
        "code": term.code,
        "name__en": str(term.name_translations.get("en", "")),
        "start_date": term.start_date.isoformat(),
        "end_date": term.end_date.isoformat(),
        "sessions-TOTAL_FORMS": "0",
        "sessions-INITIAL_FORMS": "0",
        "windows-TOTAL_FORMS": str(len(windows or [])),
        "windows-INITIAL_FORMS": "0",
        **fields,
    }
    for index, window in enumerate(windows or []):
        data.update({f"windows-{index}-{name}": value for name, value in window.items()})
    return data


REFERENCE_LISTS = [
    "/admin/institution/country/",
    "/admin/institution/language/",
    "/admin/institution/lookuptype/",
    "/admin/organization/orgunittype/",
    "/admin/organization/orgunit/",
    "/admin/organization/program/",
    "/admin/facility/building/",
    "/admin/facility/room/",
    "/admin/term/termtype/",
    "/admin/term/academicyear/",
    "/admin/term/term/",
    "/admin/term/timeslot/",
    "/admin/curriculum/coursecategory/",
    "/admin/grading/gradescale/",
    "/admin/importing/import/",
]


def test_renders_every_reference_data_page(manager: User) -> None:
    DemoReferenceSeeder()()
    client = signed_in(manager)
    pages = [
        *REFERENCE_LISTS,
        *(url + "add/" for url in REFERENCE_LISTS if "importing" not in url),
        f"/admin/organization/orgunit/{OrgUnit.objects.get(code='CSE').pk}/change/",
        f"/admin/term/term/{Term.objects.order_by('start_date').first().pk}/change/",  # type: ignore[union-attr]
        f"/admin/institution/lookuptype/{LookupType.objects.get(code='room_type').pk}/change/",
        "/admin/organization/orgunit/import-csv/",
        "/admin/organization/program/import-csv/",
        "/admin/facility/building/import-csv/",
        "/admin/facility/room/import-csv/",
        "/admin/institution/lookuptype/import-csv/",
        f"/admin/grading/gradescale/{GradeScaleFactory().pk}/change/",
        "/admin/organization/orgunit/?current=all&q=Computer",
        "/admin/institution/country/?q=대한",
    ]
    for url in pages:
        response = client.get(url)
        assert response.status_code == 200, url


def test_searches_translated_names_in_every_language(manager: User) -> None:
    client = signed_in(manager)

    response = client.get("/admin/institution/country/?q=대한민국")

    assert response.status_code == 200
    assert "KR" in response.content.decode()
    assert "JP" not in response.content.decode()


def test_lets_viewers_look_but_not_change() -> None:
    viewer = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.REFERENCE_DATA_VIEW])
    other = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])

    response = signed_in(viewer).get("/admin/institution/country/")
    assert response.status_code == 200
    assert "/admin/institution/country/add/" not in response.content.decode()
    assert signed_in(viewer).get("/admin/organization/orgunit/add/").status_code == 403
    assert signed_in(other).get("/admin/organization/orgunit/").status_code == 403


def test_creates_an_org_unit_with_translated_names(manager: User) -> None:
    department = OrgUnitType.objects.get(code="department")

    response = signed_in(manager).post(
        "/admin/organization/orgunit/add/",
        {
            "code": "NURS",
            "org_unit_type": str(department.pk),
            "name__en": "Nursing",
            "name__ko": "간호학과",
            "effective_start_date": "2026-03-01",
            "sort_order": "0",
            "successions-TOTAL_FORMS": "0",
            "successions-INITIAL_FORMS": "0",
        },
    )

    assert response.status_code == 302, response.context["adminform"].form.errors
    assert OrgUnit.objects.get(code="NURS").name_translations == {"en": "Nursing", "ko": "간호학과"}


def test_fills_every_translation_when_editing_and_clears_emptied_languages(manager: User) -> None:
    country = Country.objects.get(code="KR")
    client = signed_in(manager)

    page = client.get(f"/admin/institution/country/{country.pk}/change/").content.decode()
    assert country.name_translations["ko"] in page and country.name_translations["zh-hans"] in page

    response = client.post(
        f"/admin/institution/country/{country.pk}/change/",
        {
            "code": "KR",
            "alpha3_code": "KOR",
            "numeric_code": "410",
            "name__en": "Korea, Republic of",
            "name__ko": "대한민국",
            "name__zh-hans": "",
            "name__lo": "",
            "is_active": "on",
        },
    )

    assert response.status_code == 302
    country.refresh_from_db()
    assert country.name_translations == {"en": "Korea, Republic of", "ko": "대한민국"}


def test_explains_instead_of_failing_when_deleting_a_building_that_has_rooms(manager: User) -> None:
    building = BuildingFactory()
    RoomFactory(building=building)
    client = signed_in(manager)

    response = client.post(f"/admin/facility/building/{building.pk}/delete/", {"post": "yes"}, follow=True)

    assert response.status_code == 200
    assert "Still in use" in response.content.decode()
    assert Building.objects.filter(pk=building.pk).exists()


def test_deletes_a_building_nobody_uses(manager: User) -> None:
    building = BuildingFactory()

    response = signed_in(manager).post(f"/admin/facility/building/{building.pk}/delete/", {"post": "yes"})

    assert response.status_code == 302
    assert not Building.objects.filter(pk=building.pk).exists()


def test_reorganizes_an_org_unit_from_the_change_page(manager: User) -> None:
    old = OrgUnitFactory(effective_start_date=date(2000, 3, 1))
    new = OrgUnitFactory()
    client = signed_in(manager)

    assert "reorganize" in client.get(f"/admin/organization/orgunit/{old.pk}/change/").content.decode()
    response = client.post(
        f"/admin/organization/orgunit/{old.pk}/reorganize/",
        {
            "_form_submitted": "on",
            "change_type": "merged",
            "successors": [str(new.pk)],
            "effective_date": "2026-03-01",
            "reason": "Merger",
        },
    )

    assert response.status_code == 302
    old.refresh_from_db()
    assert old.effective_end_date == date(2026, 2, 28)


def test_shows_a_reorganization_the_action_refuses(manager: User) -> None:
    old = OrgUnitFactory(effective_start_date=date(2020, 3, 1))
    response = signed_in(manager).post(
        f"/admin/organization/orgunit/{old.pk}/reorganize/",
        {
            "_form_submitted": "on",
            "change_type": "renamed",
            "successors": [str(OrgUnitFactory().pk)],
            "effective_date": "2019-01-01",
            "reason": "x",
        },
        follow=True,
    )

    assert "The effective date must be after the unit started." in response.content.decode()
    old.refresh_from_db()
    assert old.effective_end_date is None


def test_adds_a_staggered_window_with_eligibility_and_changes_the_term_status(manager: User) -> None:
    term = TermFactory()
    client = signed_in(manager)

    response = client.post(
        f"/admin/term/term/{term.pk}/change/",
        term_form(
            term,
            [
                {
                    "window_type": TermWindowType.REGISTRATION.value,
                    "opens_at_0": "2026-11-01",
                    "opens_at_1": "09:00",
                    "closes_at_0": "2026-11-05",
                    "closes_at_1": "18:00",
                    "eligibility__year_levels": "4",
                    "eligibility__admission_year_from": "2022",
                }
            ],
        ),
    )

    assert response.status_code == 302, response.context and response.context["errors"]
    assert term.windows.get().eligibility.to_dict() == {"admission_year_from": 2022, "year_levels": [4]}

    response = client.post(
        f"/admin/term/term/{term.pk}/change-status/",
        {"_form_submitted": "on", "status": TermStatus.PUBLISHED.value},
    )

    assert response.status_code == 302
    term.refresh_from_db()
    assert term.status == TermStatus.PUBLISHED


def test_refuses_dates_that_would_leave_sessions_outside_the_term(manager: User) -> None:
    from tests.factories.term import TermSessionFactory

    term = TermFactory(start_date=date(2026, 9, 1), end_date=date(2026, 12, 20))
    TermSessionFactory(term=term, code="I", start_date=date(2026, 11, 1), end_date=date(2026, 11, 21))

    response = signed_in(manager).post(f"/admin/term/term/{term.pk}/change/", term_form(term, end_date="2026-11-15"))

    assert response.status_code == 200
    assert "Some sessions would fall outside the new dates." in response.content.decode()


def test_copies_session_windows_from_the_term_page(manager: User) -> None:
    from tests.factories.term import TermSessionFactory, TermWindowFactory

    term = TermFactory(start_date=date(2026, 9, 1), end_date=date(2026, 12, 20))
    TermWindowFactory(
        term=term,
        window_type=TermWindowType.ADD_DROP,
        opens_at=datetime(2026, 9, 1, 9, tzinfo=ZoneInfo("UTC")),
        closes_at=datetime(2026, 9, 5, 18, tzinfo=ZoneInfo("UTC")),
    )
    second = TermSessionFactory(term=term, code="B", start_date=date(2026, 10, 26), end_date=date(2026, 12, 10))
    url = f"/admin/term/term/{term.pk}/sessions/{second.pk}/copy-windows/"
    client = signed_in(manager)

    assert client.get(url).status_code == 200
    response = client.post(url, {"source": str(term.full_term_session().pk)})

    assert response.status_code == 302
    assert second.windows.count() == 1


def test_assigns_a_role_scoped_to_an_org_unit_from_the_picker(manager: User) -> None:
    user = UserFactory()
    unit = OrgUnitFactory()
    role = RoleFactory()

    response = signed_in(manager).post(
        f"/admin/security/user/{user.pk}/assign-role/",
        {
            "role": str(role.pk),
            "scope_type": ScopeType.ORG_UNIT.value,
            "scope_org_unit": str(unit.pk),
            "reason": "Department assistant",
        },
    )

    assert response.status_code == 302
    assignment = user.role_assignments.get()
    assert assignment.scope_id == unit.pk
    assert unit.code in assignment.describe_scope()


def test_requires_a_scope_target_for_a_scoped_assignment(manager: User) -> None:
    user = UserFactory()

    response = signed_in(manager).post(
        f"/admin/security/user/{user.pk}/assign-role/",
        {"role": str(RoleFactory().pk), "scope_type": ScopeType.PROGRAM.value, "reason": "x"},
    )

    assert response.status_code == 200
    assert not user.role_assignments.exists()


def test_enters_window_times_in_the_institution_time_zone_and_stores_them_in_utc(
    manager: User, set_institution_settings: Callable[..., None]
) -> None:
    set_institution_settings(timezone="Asia/Seoul")
    term = TermFactory()

    response = signed_in(manager).post(
        f"/admin/term/term/{term.pk}/change/",
        term_form(
            term,
            [
                {
                    "window_type": TermWindowType.REGISTRATION.value,
                    "opens_at_0": "2026-11-02",
                    "opens_at_1": "10:00",
                    "closes_at_0": "2026-11-05",
                    "closes_at_1": "18:00",
                }
            ],
        ),
    )

    assert response.status_code == 302
    assert term.windows.get().opens_at.astimezone(ZoneInfo("UTC")) == datetime(
        2026, 11, 2, 1, 0, tzinfo=ZoneInfo("UTC")
    )


def test_keeps_class_period_times_as_entered_without_time_zone_conversion(
    manager: User, set_institution_settings: Callable[..., None]
) -> None:
    set_institution_settings(timezone="Asia/Seoul")

    response = signed_in(manager).post(
        "/admin/term/timeslot/add/",
        {
            "code": "P1",
            "name__en": "Period 1",
            "start_time": "09:00",
            "end_time": "09:50",
            "weekdays": ["1", "2", "3", "4", "5"],
            "sort_order": "0",
            "is_active": "on",
        },
    )

    assert response.status_code == 302, response.context["adminform"].form.errors
    slot = TimeSlot.objects.get(code="P1")
    assert slot.start_time == time(9, 0)
    assert slot.weekdays == [1, 2, 3, 4, 5]


def _upload(rows: list[list[str]]) -> SimpleUploadedFile:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    return SimpleUploadedFile("org.csv", buffer.getvalue().encode(), content_type="text/csv")


def test_imports_a_csv_file_from_the_list_and_shows_the_failed_rows(manager: User) -> None:
    client = signed_in(manager)
    upload = _upload(
        [
            ["code", "type", "name_en", "effective_start_date"],
            ["UNI", "university", "Sample University", "1990-03-01"],
            ["BAD", "no_such_type", "Unknown", "1990-03-01"],
        ]
    )

    response = client.post("/admin/organization/orgunit/import-csv/", {"file": upload}, follow=True)

    assert response.status_code == 200
    page = response.content.decode()
    assert "1 row(s) imported." in page
    assert "1 row(s) failed" in page
    import_run = Import.objects.get()
    assert import_run.user_id == manager.pk and import_run.importer == "org_units"
    assert OrgUnit.objects.filter(code="UNI").exists()

    download = client.get(f"/admin/importing/import/{import_run.pk}/failed-rows/")
    assert download.status_code == 200
    rows = list(csv.reader(io.StringIO(download.content.decode())))
    assert rows[1][-1] == 'Unknown type code "no_such_type".'


def test_refuses_a_csv_file_without_the_required_columns(manager: User) -> None:
    response = signed_in(manager).post(
        "/admin/organization/orgunit/import-csv/", {"file": _upload([["code", "name_en"], ["UNI", "Sample"]])}
    )

    assert response.status_code == 200
    assert "Missing required columns: type, effective_start_date." in response.content.decode()
    assert not Import.objects.exists()


def test_needs_the_import_permission_for_the_csv_import() -> None:
    editor = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.ORG_UNITS_MANAGE])

    assert signed_in(editor).get("/admin/organization/orgunit/import-csv/").status_code == 403


def test_keeps_the_default_grade_scale_fixed(manager: User) -> None:
    scale = GradeScaleFactory(is_default=True)
    other = GradeScaleFactory()

    response = signed_in(manager).post(
        f"/admin/grading/gradescale/{other.pk}/change/",
        {
            "code": other.code,
            "name__en": "Other",
            "max_grade_points": "4.5",
            "is_default": "on",
            "items-TOTAL_FORMS": "0",
            "items-INITIAL_FORMS": "0",
        },
    )

    assert response.status_code == 302
    other.refresh_from_db()
    scale.refresh_from_db()
    assert scale.is_default and not other.is_default


def test_hides_reference_data_from_users_without_the_view_permission() -> None:
    other = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])

    page = signed_in(other).get("/admin/").content.decode()

    assert "/admin/institution/country/" not in page


def _assign(user: User, role_name: str) -> Any:
    from ninefruits.security.actions import AssignRole

    return AssignRole()(user, Role.objects.get(name=role_name), "test")


def test_lets_academic_affairs_manage_the_reference_data() -> None:
    staff = UserFactory()
    _assign(staff, "academic_affairs")

    assert signed_in(staff).get("/admin/term/term/add/").status_code == 200


@pytest.mark.parametrize(("locale", "texts"), [("ko", ["기준정보", "조직 단위"]), ("zh-hans", ["组织单位"])])
def test_renders_the_reference_pages_in_korean_and_chinese(manager: User, locale: str, texts: list[str]) -> None:
    manager.locale = locale
    manager.save()

    page = signed_in(manager).get("/admin/organization/orgunit/").content.decode()

    for text in texts:
        assert text in page


def test_shows_users_only_their_own_imports() -> None:
    from ninefruits.importing.services import start_import

    owner = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.STUDENT_RECORDS_MANAGE])
    other = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS])
    import_run = start_import("buildings", owner, "b.csv", "b.csv", [{"code": "SCI", "name_en": "Science"}])

    assert signed_in(owner).get(f"/admin/importing/import/{import_run.pk}/change/").status_code == 200
    assert signed_in(other).get(f"/admin/importing/import/{import_run.pk}/change/").status_code in (302, 403)
    assert signed_in(other).get(f"/admin/importing/import/{import_run.pk}/failed-rows/").status_code == 403


def test_reference_policies_answer_for_records(manager: User) -> None:
    viewer = UserFactory(permissions=[Permission.ADMIN_PANEL_ACCESS, Permission.REFERENCE_DATA_VIEW])
    building = BuildingFactory()

    assert viewer.has_perm("view", building) and not viewer.has_perm("update", building)
    assert manager.has_perm("update", building) and manager.has_perm("delete", building)
