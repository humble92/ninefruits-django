"""Fixtures for the admission tests (original ``beforeEach`` of tests/Feature/Admission)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from ninefruits.admission.settings import AdmissionSettings
from ninefruits.security.enums import MfaEnforcement
from ninefruits.settings.groups.security import SecuritySettings
from tests.reference_conftest import *  # noqa: F403


@pytest.fixture
def admission_reference(essential_data: None) -> None:
    """Essential data and the Korean university profile (admission types, document types)."""
    from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder

    KoreanUniversityProfileSeeder()()


@pytest.fixture
def mfa_disabled(db: None) -> None:
    settings = SecuritySettings.load()
    settings.mfa_enforcement = MfaEnforcement.DISABLED
    settings.save()


@pytest.fixture
def set_admission_settings(db: None) -> Callable[..., None]:
    def set_values(**values: Any) -> None:
        settings = AdmissionSettings.load()
        for name, value in values.items():
            setattr(settings, name, value)
        settings.save()

    return set_values


@pytest.fixture
def diploma(admission_reference: None) -> Any:
    from ninefruits.admission.models import DOCUMENT_TYPE_LOOKUP
    from ninefruits.institution.models import LookupValue

    return LookupValue.objects.of_type(DOCUMENT_TYPE_LOOKUP).get(code="diploma")
