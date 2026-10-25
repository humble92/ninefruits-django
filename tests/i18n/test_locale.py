"""Port of tests/Feature/I18n/LocaleTest.php: locale negotiation (user > session > browser >
institution default), the locale switcher, the database session locale and translatable columns."""

from __future__ import annotations

import pytest
from django.contrib.messages import get_messages
from django.db import IntegrityError, connection, transaction
from django.test import Client, RequestFactory
from django.utils import translation

from ninefruits.core.db import session_context
from ninefruits.i18n.middleware import SESSION_KEY, resolve_locale
from ninefruits.institution.services.supported_locales import SupportedLocales, has_catalog
from ninefruits.security.models import Role, User
from ninefruits.settings.groups.institution import InstitutionSettings

pytestmark = [pytest.mark.django_db, pytest.mark.urls("tests.i18n.urls")]


def make_user(**fields: object) -> User:
    return User.objects.create_user(
        email=f"locale{User.objects.count()}@example.test", password="secret-pass", **fields
    )


def language_of(response: object) -> str:
    return response.content.decode().split("|")[0]  # type: ignore[attr-defined]


def test_uses_the_browser_language_when_supported(client: Client) -> None:
    response = client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="zh-CN,zh;q=0.9")
    assert response.content.decode() == "zh-hans|语言"
    assert response.headers["Content-Language"] == "zh-hans"
    assert client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="ko-KR,ko;q=0.9").content.decode() == "ko|언어"
    assert client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="fr-FR").content.decode() == "en|Language"


def test_browser_language_order_and_variants(client: Client) -> None:
    assert language_of(client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="fr;q=1, ko;q=0.5")) == "ko"
    assert language_of(client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="en;q=0.4, ko;q=0.8")) == "ko"
    assert language_of(client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="zh-Hans-CN")) == "zh-hans"
    assert language_of(client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="zh")) == "zh-hans"
    # Traditional Chinese is a different script: never served Simplified Chinese.
    assert language_of(client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="zh-TW")) == "en"


def test_ships_lao_as_a_supported_language(client: Client) -> None:
    # Added 2026-10-23 for the first Lao customer: catalogs plus the settings migration default.
    assert "lo" in SupportedLocales().all()
    assert has_catalog("lo")
    assert client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="lo-LA,lo;q=0.9").content.decode() == "lo|ພາສາ"


def test_prefers_the_language_chosen_by_the_user(client: Client) -> None:
    client.force_login(make_user(locale="ko"))
    assert language_of(client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="en")) == "ko"


def test_session_choice_comes_before_the_browser_language(client: Client) -> None:
    session = client.session
    session[SESSION_KEY] = "lo"
    session.save()
    assert language_of(client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="ko")) == "lo"


def test_falls_back_to_the_institution_default() -> None:
    settings = InstitutionSettings.load()
    settings.default_locale = "ko"
    settings.save()
    request = RequestFactory().get("/", HTTP_ACCEPT_LANGUAGE="fr")
    assert resolve_locale(request) == "ko"

    settings.default_locale = "xx"  # not offered: the fallback language
    settings.save()
    assert resolve_locale(RequestFactory().get("/")) == "en"


def test_ignores_stored_languages_that_are_no_longer_offered(client: Client) -> None:
    settings = InstitutionSettings.load()
    settings.supported_locales = ["en", "ko"]
    settings.save()
    client.force_login(make_user(locale="zh-hans"))
    assert language_of(client.get("/_test/language/", HTTP_ACCEPT_LANGUAGE="ko")) == "ko"


def test_switches_the_language_and_stores_it_for_signed_in_users(client: Client) -> None:
    user = make_user()
    client.force_login(user)

    response = client.post("/i18n/locale/", {"locale": "zh-hans"}, HTTP_REFERER="/portal/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/portal/"
    user.refresh_from_db()
    assert user.locale == "zh-hans"
    assert client.session[SESSION_KEY] == "zh-hans"


def test_switches_the_language_for_guests_in_the_session(client: Client) -> None:
    response = client.post("/i18n/locale/", {"language": "lo", "next": "https://evil.example/"})
    assert response.headers["Location"] == "/"
    assert client.session[SESSION_KEY] == "lo"


def test_rejects_languages_the_institution_does_not_offer(client: Client) -> None:
    settings = InstitutionSettings.load()
    settings.supported_locales = ["en", "ko"]
    settings.save()

    for locale in ("zh-hans", "xx"):
        response = client.post("/i18n/locale/", {"locale": locale})
        assert response.status_code == 302
        assert SESSION_KEY not in client.session
        assert [m.level_tag for m in get_messages(response.wsgi_request)][-1:] == ["error"]


def test_locale_switch_accepts_only_post(client: Client) -> None:
    assert client.get("/i18n/locale/").status_code == 405


def test_passes_the_locale_and_user_to_the_database_session_and_clears_them_after_the_request(
    client: Client,
) -> None:
    user = make_user()
    client.force_login(user)

    response = client.get("/_test/database-context/", HTTP_ACCEPT_LANGUAGE="ko")

    assert response.json()["app.locale"] == "ko"
    assert response.json()["app.fallback_locale"] == "en"
    assert response.json()["app.user_id"] == str(user.pk)
    assert response.json()["app.actor"] == f"user:{user.pk}"
    current = session_context().current()
    assert current["app.locale"] == ""
    assert current["app.user_id"] == ""


def test_returns_translatable_attributes_in_the_current_locale_with_fallback() -> None:
    role = Role.objects.create(
        name="registrar_test", guard_name="web", display_name={"en": "Registrar", "ko": "학적 담당"}
    )
    role = Role.objects.get(pk=role.pk)

    with translation.override("ko"):
        assert role.display_name == "학적 담당"
    with translation.override("zh-hans"):
        assert role.display_name == "Registrar"


def test_keeps_translatable_columns_as_json_objects_in_the_database() -> None:
    role = Role.objects.create(name="object_check_test", guard_name="web", display_name={"en": "Registrar"})
    with pytest.raises(IntegrityError, match="roles_display_name_object_check"), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("UPDATE roles SET display_name = %s::jsonb WHERE id = %s", ['"plain text"', role.pk])
