"""Locale aware dates and numbers (original Carbon ``isoFormat`` and ``Illuminate\\Support\\Number``
with the locale set by ``SetLocale``). Babel (CLDR) does the formatting in the active language;
datetimes are shown in the institution time zone, as the original views did with
``->timezone(InstitutionSettings::timezone)``.

    format_ll(date)        # Carbon isoFormat('LL'):  "October 24, 2026" / "2026년 10월 24일"
    format_lll(datetime)   # isoFormat('LLL'):        "October 24, 2026 3:04 PM"
    format_ll_ddd(date)    # isoFormat('ll (ddd)'):   "Oct 24, 2026 (Sat)"
    format_number(1234.5)  # Number::format:          "1,234.5" / "1.234,5" (lo)

Template filters: ``{% load nf_i18n %}`` then ``{{ value|ll }}``, ``|lll``, ``|ll_ddd``,
``|number``, ``|percent``.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from babel import Locale, dates, numbers
from django.utils import timezone
from django.utils.translation import to_locale

from ninefruits.i18n.translation import current_language


def babel_locale(language: str | None = None) -> Locale:
    """Babel locale for a Django language code (``zh-hans`` -> ``zh_Hans``); English when unknown."""
    try:
        return Locale.parse(to_locale(language or current_language()))
    except ValueError, LookupError:
        return Locale.parse("en")


def institution_timezone() -> ZoneInfo:
    from ninefruits.settings.groups.base import MissingSettings
    from ninefruits.settings.groups.institution import InstitutionSettings

    try:
        return ZoneInfo(InstitutionSettings.load().timezone)
    except MissingSettings:
        return ZoneInfo(str(timezone.get_default_timezone()))


def _local(value: datetime) -> datetime:
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_default_timezone())
    return value.astimezone(institution_timezone())


def _as_date(value: date | datetime) -> date:
    return _local(value).date() if isinstance(value, datetime) else value


def format_ll(value: date | datetime | None, language: str | None = None) -> str:
    if value is None:
        return ""
    return dates.format_date(_as_date(value), "long", locale=babel_locale(language))


def format_lll(value: datetime | None, language: str | None = None) -> str:
    if value is None:
        return ""
    locale = babel_locale(language)
    local = _local(value)
    return (
        f"{dates.format_date(local.date(), 'long', locale=locale)} {dates.format_time(local, 'short', locale=locale)}"
    )


def format_ll_ddd(value: date | datetime | None, language: str | None = None) -> str:
    if value is None:
        return ""
    locale = babel_locale(language)
    day = _as_date(value)
    return f"{dates.format_date(day, 'medium', locale=locale)} ({dates.format_date(day, 'EEE', locale=locale)})"


def format_number(value: int | float | Decimal | None, language: str | None = None, decimals: int | None = None) -> str:
    if value is None:
        return ""
    locale = babel_locale(language)
    if decimals is None:
        return numbers.format_decimal(value, locale=locale)
    return numbers.format_decimal(value, format=f"#,##0.{'0' * decimals}" if decimals else "#,##0", locale=locale)


def format_percent(value: int | float | Decimal | None, language: str | None = None) -> str:
    """``value`` is a fraction (0.25 -> "25%")."""
    if value is None:
        return ""
    return numbers.format_percent(value, locale=babel_locale(language))


def format_currency(value: int | float | Decimal | None, currency: str, language: str | None = None) -> str:
    if value is None:
        return ""
    return numbers.format_currency(value, currency, locale=babel_locale(language))
