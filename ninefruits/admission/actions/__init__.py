"""Admission business actions (original ``App\\Domain\\Admission\\Actions``)."""

from .applications import (
    AttachApplicationDocument,
    StartApplication,
    SubmitApplication,
    UpdateApplicantPersonalDetails,
    UpdateApplication,
    WithdrawApplication,
    can_edit_identity,
)
from .decisions import DecideApplication, ReleaseDecisions, RespondToOffer
from .matriculation import ExpireDraftApplications, MatriculateApplicant
from .registration import RegisterApplicant

__all__ = [
    "AttachApplicationDocument",
    "DecideApplication",
    "ExpireDraftApplications",
    "MatriculateApplicant",
    "RegisterApplicant",
    "ReleaseDecisions",
    "RespondToOffer",
    "StartApplication",
    "SubmitApplication",
    "UpdateApplicantPersonalDetails",
    "UpdateApplication",
    "WithdrawApplication",
    "can_edit_identity",
]
