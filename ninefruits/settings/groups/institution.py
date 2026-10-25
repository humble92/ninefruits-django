"""Per-installation settings (settings group ``institution``, original
``App\\Domain\\Institution\\Settings\\InstitutionSettings``)."""

from __future__ import annotations

from typing import ClassVar
from zoneinfo import available_timezones

from pydantic import field_validator

from ninefruits.settings.groups.base import SettingsGroup


class InstitutionSettings(SettingsGroup):
    group: ClassVar[str] = "institution"

    #: Institution name by language code (``{"en": "...", "ko": "..."}``).
    name: dict[str, str]
    #: Languages offered to users (Django codes ``en``, ``ko``, ``zh-hans``, ``lo``). Each needs
    #: a translation catalog (``locale/<lang>/``).
    supported_locales: list[str]
    default_locale: str
    #: IANA time zone used for academic calendar decisions. Stored times are UTC.
    timezone: str

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str) -> str:
        if value != "UTC" and value not in available_timezones():
            raise ValueError(f"Unknown time zone {value!r}.")
        return value
