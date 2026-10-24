"""Admission options (settings group ``admissions``, original
``App\\Domain\\Admission\\Settings\\AdmissionSettings``)."""

from __future__ import annotations

from typing import ClassVar

from ninefruits.settings.groups.base import SettingsGroup


class AdmissionSettings(SettingsGroup):
    group: ClassVar[str] = "admissions"

    #: Whether people can create an account themselves to apply.
    applicant_registration_enabled: bool
    #: Drafts not touched for this many days expire (``admission_expire_drafts``). Drafts in a
    #: cycle that has closed expire regardless.
    draft_expiry_days: int
    #: Largest uploaded document, in megabytes.
    max_document_size_mb: int
