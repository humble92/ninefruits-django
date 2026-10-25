"""Locales offered by this installation (original ``App\\Domain\\Institution\\Services\\SupportedLocales``).

The institution's supported locales that have a translation catalog (``locale/<lang>/`` in
``LOCALE_PATHS``, an app or Django itself). Adding a language = adding the catalogs + enabling it
in the institution settings. Nothing in code lists languages.

Language codes are Django's (``en``, ``ko``, ``zh-hans``, ``lo``); catalog directories use the
locale name (``zh_Hans``).
"""

from __future__ import annotations

import logging
from functools import cache
from pathlib import Path

from babel import Locale, UnknownLocaleError
from django.apps import apps
from django.conf import settings
from django.conf.locale import LANG_INFO
from django.http import HttpRequest
from django.utils.translation import to_locale
from django.utils.translation.trans_real import parse_accept_lang_header

from ninefruits.i18n.translation import base_language, fallback_language

logger = logging.getLogger(__name__)


@cache
def _catalog_roots() -> tuple[Path, ...]:
    """The application's own catalogs: ``LOCALE_PATHS`` and the ``locale/`` of Ninefruits apps
    (not Django's or third party catalogs, which exist for many languages we do not offer)."""
    roots = [Path(path) for path in settings.LOCALE_PATHS]
    roots += [
        Path(config.path) / "locale" for config in apps.get_app_configs() if config.name.startswith("ninefruits.")
    ]
    return tuple(root for root in roots if root.is_dir())


def has_catalog(code: str) -> bool:
    """A ``<locale>/LC_MESSAGES`` directory exists for the language in the application's catalogs
    (original ``is_dir(lang_path($locale))``)."""
    name = to_locale(code)
    return any((root / name / "LC_MESSAGES").is_dir() for root in _catalog_roots())


def normalize(code: str) -> str:
    """Browser or Laravel spelling to a Django language code: ``zh_CN`` -> ``zh-cn``, ``ko-KR`` -> ``ko-kr``."""
    return code.strip().replace("_", "-").lower()


class SupportedLocales:
    def __init__(self, settings_group: object | None = None) -> None:
        self._settings = settings_group

    # -- institution settings -------------------------------------------------------------------
    def _institution(self) -> tuple[list[str], str]:
        from ninefruits.settings.groups.base import MissingSettings
        from ninefruits.settings.groups.institution import InstitutionSettings

        try:
            group = self._settings or InstitutionSettings.load()
        except MissingSettings:
            # Settings rows are created by migrations; an emptied table (tests flushing all
            # tables) must not take every page down.
            logger.warning("institution settings are missing; using the configured languages")
            return [code for code, _ in settings.LANGUAGES], settings.LANGUAGE_CODE
        return list(group.supported_locales), str(group.default_locale)  # type: ignore[attr-defined]

    def all(self) -> list[str]:
        supported, _default = self._institution()
        fallback = fallback_language()
        locales = [code for code in supported if has_catalog(code) or code == fallback]
        return list(dict.fromkeys([*locales, fallback]))

    def is_supported(self, locale: str | None) -> bool:
        return locale is not None and locale in self.all()

    def default(self) -> str:
        _supported, default = self._institution()
        return default if self.is_supported(default) else fallback_language()

    def negotiate(self, request: HttpRequest) -> str | None:
        """The first ``Accept-Language`` entry (by quality) that matches a supported locale:
        the exact code, its Django fallbacks (``zh-cn`` -> ``zh-hans``), then its base language
        (``ko-kr`` -> ``ko``; ``zh`` -> the only offered ``zh-*`` variant)."""
        header = request.headers.get("Accept-Language", "")
        supported = self.all()
        lowered = {code.lower(): code for code in supported}
        for language, _quality in parse_accept_lang_header(header):
            if language == "*":
                continue
            candidate = normalize(language)
            fallbacks = LANG_INFO.get(candidate, {}).get("fallback", [])
            for option in [candidate, *fallbacks, base_language(candidate)]:
                if option in lowered:
                    return lowered[option]
            if fallbacks:  # e.g. zh-tw -> zh-hant: never a different script
                continue
            variants = [code for code in supported if code.lower().startswith(base_language(candidate) + "-")]
            if len(variants) == 1:
                return variants[0]
        return None

    @staticmethod
    def label(locale: str) -> str:
        """The language name written in that language, e.g. "한국어", "中文 (简体)", "ລາວ"."""
        try:
            return Locale.parse(to_locale(locale)).get_display_name(to_locale(locale)) or locale
        except UnknownLocaleError, ValueError:
            return locale

    def choices(self) -> list[tuple[str, str]]:
        return [(code, self.label(code)) for code in self.all()]


def available_catalog_locales() -> list[str]:
    """Every language that has a catalog in this installation (options of the institution
    settings page; original ``File::directories(lang_path())``)."""
    codes = {fallback_language()}
    for root in _catalog_roots():
        for child in root.iterdir():
            if (child / "LC_MESSAGES").is_dir():
                codes.add(child.name.replace("_", "-").lower())
    configured = [code for code, _ in settings.LANGUAGES]
    return [code for code in configured if code in codes] + sorted(codes - set(configured))
