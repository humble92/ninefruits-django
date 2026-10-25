"""Language resolution shared by translatable values (porting-plan 6.2).

The order is the one of the database function ``util.i18n(value, locale, fallback)``
(``db/sql/functions/i18n.sql``): requested language, its base language (``zh-hans`` -> ``zh``),
the fallback language, then the first non-empty value by key order. ``translate()`` gives the
same answer in Python so that ``obj.title`` and ``ORDER BY util.i18n(title)`` agree.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.utils import translation


def fallback_language() -> str:
    return str(getattr(settings, "FALLBACK_LANGUAGE", settings.LANGUAGE_CODE))


def current_language() -> str:
    return translation.get_language() or settings.LANGUAGE_CODE


def base_language(code: str) -> str:
    """``zh-hans`` -> ``zh``, ``pt_BR`` -> ``pt`` (the SQL ``split_part(replace(..., '-', '_'), '_', 1)``)."""
    return code.replace("-", "_").split("_", 1)[0]


def translate(value: Mapping[str, Any] | None, language: str | None = None, fallback: str | None = None) -> str | None:
    """The value for ``language`` (default: the active language), like ``util.i18n``.

    Returns ``None`` when ``value`` is not a mapping (SQL: not a jsonb object)."""
    if not isinstance(value, Mapping):
        return None
    language = language or current_language()
    fallback = fallback or fallback_language()
    for key in (language, base_language(language), fallback):
        text = value.get(key)
        if text not in (None, ""):
            return str(text)
    for key in sorted(value):
        text = value[key]
        if text not in (None, ""):
            return str(text)
    return None


def search_text(value: Mapping[str, Any] | None) -> str:
    """All translations joined by a space in key order (``util.i18n_search_text``)."""
    if not isinstance(value, Mapping):
        return ""
    return " ".join(str(value[key]) for key in sorted(value) if value[key] is not None)
