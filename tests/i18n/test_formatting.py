"""Locale aware dates and numbers (original Carbon isoFormat / Number with the request locale)."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from django.template import Context, Template
from django.utils import formats, translation

from ninefruits.i18n import formatting
from ninefruits.settings.groups.institution import InstitutionSettings

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _seoul() -> None:
    settings = InstitutionSettings.load()
    settings.timezone = "Asia/Seoul"
    settings.save()


def test_dates_in_each_language() -> None:
    day = date(2026, 10, 24)
    assert formatting.format_ll(day, "en") == "October 24, 2026"
    assert formatting.format_ll(day, "ko") == "2026년 10월 24일"
    assert formatting.format_ll(day, "zh-hans") == "2026年10月24日"
    assert formatting.format_ll(day, "lo") == "24 ຕຸລາ 2026"
    assert formatting.format_ll_ddd(day, "en") == "Oct 24, 2026 (Sat)"


def test_datetimes_use_the_institution_time_zone() -> None:
    moment = datetime(2026, 10, 24, 15, 4, tzinfo=UTC)  # 00:04 next day in Seoul
    assert formatting.format_lll(moment, "en").startswith("October 25, 2026 12:04")
    assert formatting.format_ll(moment, "ko") == "2026년 10월 25일"


def test_numbers_follow_the_active_language() -> None:
    with translation.override("lo"):
        assert formatting.format_number(1234.5) == "1.234,5"
    assert formatting.format_number(1234.5, "ko") == "1,234.5"
    assert formatting.format_number(3, "en", decimals=2) == "3.00"
    assert formatting.format_percent(0.25, "en") == "25%"
    assert formatting.format_number(None) == ""


def test_template_filters() -> None:
    template = Template("{% load nf_i18n %}{{ day|ll }} {{ n|number }} {{ name|i18n }}")
    with translation.override("ko"):
        rendered = template.render(Context({"day": date(2026, 10, 24), "n": 1500, "name": {"en": "A", "ko": "가"}}))
    assert rendered == "2026년 10월 24일 1,500 가"


def test_lao_has_django_formats() -> None:
    with translation.override("lo"):
        assert formats.get_format("DECIMAL_SEPARATOR") == ","
        assert formats.date_format(date(2026, 10, 24), "SHORT_DATE_FORMAT") == "24/10/2026"
    assert translation.get_language_info("lo")["name_local"] == "ລາວ"
