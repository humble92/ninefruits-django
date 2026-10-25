"""Examination actions (original ``App\\Domain\\Assessment\\Actions``). Admin screens, portal views
and commands only call these."""

from .change_session_pass_score import ChangeSessionPassScore
from .correct_assessment_result import CorrectAssessmentResult
from .record_assessment_result import RecordAssessmentResult
from .register_for_assessment import RegisterForAssessment

__all__ = ["ChangeSessionPassScore", "CorrectAssessmentResult", "RecordAssessmentResult", "RegisterForAssessment"]
