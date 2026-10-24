"""Course evaluation options (settings group ``evaluations``, original
``App\\Domain\\Evaluation\\Settings\\EvaluationSettings``). Values come from the data migrations
``appsettings.0012_p7_evaluation_settings`` and ``0013_p7_raise_minimum_response_percent``."""

from __future__ import annotations

from typing import ClassVar

from ninefruits.settings.groups.base import SettingsGroup


class EvaluationSettings(SettingsGroup):
    group: ClassVar[str] = "evaluations"

    #: While a term's evaluation is open, its grades stay hidden until the student evaluated
    #: every course.
    grades_require_evaluation: bool
    #: Refuse a response with the same answer to every scale question (legacy: all 1s or all 5s).
    reject_uniform_answers: bool
    #: Defaults for a new term's evaluation: results only above both.
    minimum_responses: int
    minimum_response_percent: int
