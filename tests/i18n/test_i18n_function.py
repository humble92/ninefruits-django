"""Port of tests/Database/I18n/I18nFunctionTest.php (``util.i18n`` and friends), plus the Django
language codes (``zh-hans``) and the Python resolution that must give the same answers."""

from __future__ import annotations

import json
from typing import Any

import pytest
from django.db import connection

from ninefruits.core.db import session_context
from ninefruits.i18n.translation import search_text, translate

pytestmark = pytest.mark.django_db


def i18n(value: Any, locale: str | None = None, fallback: str = "en") -> str | None:
    payload = json.dumps(value) if isinstance(value, dict) else value
    with connection.cursor() as cursor:
        if locale is None:
            cursor.execute("SELECT util.i18n(%s::jsonb)", [payload])
        else:
            cursor.execute("SELECT util.i18n(%s::jsonb, %s, %s)", [payload, locale, fallback])
        return cursor.fetchone()[0]


def test_returns_the_value_for_the_requested_locale() -> None:
    assert i18n({"en": "Data Structures", "ko": "데이터구조"}, "ko") == "데이터구조"


def test_falls_back_to_the_base_language_then_the_fallback_locale_then_the_first_value() -> None:
    value = {"en": "Data Structures", "zh": "数据结构"}

    assert i18n(value, "zh_CN") == "数据结构"
    assert i18n(value, "fr") == "Data Structures"
    assert i18n({"ko": "데이터구조"}, "fr") == "데이터구조"
    assert i18n({"en": "", "ko": "데이터구조"}, "en") == "데이터구조"


def test_django_language_codes_work_as_keys_and_fall_back_to_the_base_language() -> None:
    # Translatable values use the Django codes; zh-hans falls back to a plain "zh" key.
    assert i18n({"en": "Data Structures", "zh-hans": "数据结构"}, "zh-hans") == "数据结构"
    assert i18n({"en": "Data Structures", "zh": "数据结构"}, "zh-hans") == "数据结构"
    assert i18n({"en": "Data Structures", "lo": "ໂຄງສ້າງຂໍ້ມູນ"}, "lo") == "ໂຄງສ້າງຂໍ້ມູນ"
    # A zh-hans key is not the base language of zh-hant (no cross-script fallback).
    assert i18n({"en": "Data Structures", "zh-hans": "数据结构"}, "zh-hant") == "Data Structures"


def test_returns_null_for_non_object_values() -> None:
    assert i18n(None, "en") is None
    assert i18n('"plain"', "en") is None


def test_reads_the_locale_from_the_session_settings() -> None:
    context = session_context()
    context.set_locale("ko", "en")
    try:
        assert i18n({"en": "Grade", "ko": "성적"}) == "성적"
    finally:
        context.reset()


def test_joins_all_translations_for_search() -> None:
    with connection.cursor() as cursor:
        cursor.execute("""SELECT util.i18n_search_text('{"en":"Data","ko":"데이터"}'::jsonb)""")
        assert cursor.fetchone()[0] == "Data 데이터"


def test_supports_icu_collations_for_locale_aware_ordering() -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT name FROM (VALUES ('하'), ('가'), ('나')) AS t(name) ORDER BY name COLLATE "ko-x-icu" """
        )
        assert [row[0] for row in cursor.fetchall()] == ["가", "나", "하"]
        cursor.execute(
            """SELECT name FROM (VALUES ('张'), ('阿'), ('李')) AS t(name) ORDER BY name COLLATE "zh-Hans-x-icu" """
        )
        assert [row[0] for row in cursor.fetchall()] == ["阿", "李", "张"]


@pytest.mark.parametrize(
    ("value", "locale"),
    [
        ({"en": "Data Structures", "ko": "데이터구조"}, "ko"),
        ({"en": "Data Structures", "zh": "数据结构"}, "zh-hans"),
        ({"en": "Data Structures", "zh-hans": "数据结构"}, "zh-hans"),
        ({"en": "Data Structures", "zh": "数据结构"}, "fr"),
        ({"ko": "데이터구조", "lo": "ໂຄງສ້າງ"}, "fr"),
        ({"en": "", "ko": "데이터구조"}, "en"),
        ({}, "en"),
    ],
)
def test_python_resolution_matches_the_database_function(value: dict[str, str], locale: str) -> None:
    assert translate(value, locale, "en") == i18n(value, locale)


def test_python_search_text_matches_the_database_function() -> None:
    value = {"zh-hans": "数据", "en": "Data", "ko": "데이터"}
    with connection.cursor() as cursor:
        cursor.execute("SELECT util.i18n_search_text(%s::jsonb)", [json.dumps(value)])
        assert search_text(value) == cursor.fetchone()[0]
