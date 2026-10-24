"""Fixtures for the person tests."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from ninefruits.person.settings import StudentRecordSettings
from tests.reference_conftest import *  # noqa: F403


@pytest.fixture
def status_change_types(db: None) -> None:
    from ninefruits.setup.seeders.essential.status_change_type import StatusChangeTypeSeeder

    StatusChangeTypeSeeder()()


@pytest.fixture
def set_student_record_settings(db: None) -> Callable[..., None]:
    def set_values(**values: Any) -> None:
        settings = StudentRecordSettings.load()
        for name, value in values.items():
            setattr(settings, name, value)
        settings.save()

    return set_values
