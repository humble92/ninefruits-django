"""Person business actions (original ``App\\Domain\\Person\\Actions``)."""

from .additional_programs import (
    CancelAdditionalProgramRequest,
    DecideAdditionalProgramRequest,
    EndAdditionalProgram,
    RequestAdditionalProgram,
)
from .advisors import AssignAdvisor
from .contact import UpdateOwnContactDetails
from .invitations import AcceptInvitation, InvitePerson
from .merge import MergePeople
from .status_changes import CancelStatusChange, DecideStatusChange, RecordStatusChange, RequestStatusChange
from .students import RegisterStudent

__all__ = [
    "AcceptInvitation",
    "AssignAdvisor",
    "CancelAdditionalProgramRequest",
    "CancelStatusChange",
    "DecideAdditionalProgramRequest",
    "DecideStatusChange",
    "EndAdditionalProgram",
    "InvitePerson",
    "MergePeople",
    "RecordStatusChange",
    "RegisterStudent",
    "RequestAdditionalProgram",
    "RequestStatusChange",
    "UpdateOwnContactDetails",
]
