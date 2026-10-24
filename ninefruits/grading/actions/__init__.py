"""Grading actions (original ``App\\Domain\\Grading\\Actions``) needed by the reference data
screens. The grade workflow actions arrive with Phase 6."""

from .save_grade_scale import SaveGradeScale

__all__ = ["SaveGradeScale"]
