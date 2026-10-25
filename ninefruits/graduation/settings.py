"""Graduation options (settings group ``graduation``, original
``App\\Domain\\Graduation\\Settings\\GraduationSettings``). Values come from the data migrations
``appsettings.0015_p11_graduation_settings`` and ``0016_p11_graduation_defaults``."""

from __future__ import annotations

import re
from typing import ClassVar

from ninefruits.settings.groups.base import SettingsGroup

#: Literal text and {PROGRAM}, {YYYY}, {YY} tokens, then exactly one {SEQ:n} (original form regex).
DEGREE_NUMBER_PATTERN = re.compile(r"^[^{}]*(\{(PROGRAM|YYYY|YY)\}[^{}]*)*\{SEQ:\d{1,2}\}[^{}]*$")


class GraduationSettings(SettingsGroup):
    group: ClassVar[str] = "graduation"

    #: Degree number pattern: {YYYY}/{YY} graduation year, {PROGRAM} program code, {SEQ:n} sequence per prefix.
    degree_number_pattern: str
    #: Cumulative GPA required to graduate; None for none.
    minimum_cumulative_gpa: float | None
