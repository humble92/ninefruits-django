"""Certificate options (settings group ``certificates``, original
``App\\Domain\\Certificate\\Settings\\CertificateSettings``). Values come from the data migration
``appsettings.0014_p8_certificate_settings``."""

from __future__ import annotations

import re
from typing import ClassVar

from pydantic import field_validator

from ninefruits.settings.groups.base import SettingsGroup

#: Literal text and {TYPE}, {YYYY}, {YY} tokens, then exactly one {SEQ:n} (original form regex).
SERIAL_PATTERN = re.compile(r"^[^{}]*(\{(TYPE|YYYY|YY)\}[^{}]*)*\{SEQ:\d{1,2}\}[^{}]*$")


class CertificateSettings(SettingsGroup):
    group: ClassVar[str] = "certificates"

    #: Serial number pattern: {TYPE} type code, {YYYY}/{YY} issue year, {SEQ:n} sequence per prefix.
    serial_pattern: str
    #: Days the public verification page confirms an issue; 0 for no limit.
    verification_valid_days: int
    #: Default signer by locale, used when a template has none (e.g. the president's title).
    signer: dict[str, str]

    @field_validator("signer", mode="before")
    @classmethod
    def _signer_object(cls, value: object) -> object:
        # spatie stores an empty PHP array as a JSON list.
        return {} if value == [] else value
