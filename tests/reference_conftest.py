"""Fixtures shared by the reference data test packages (imported by their conftest.py)."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from django.core.cache import cache
from django.utils import translation

from ninefruits.security.services.authorization import begin_scope
from ninefruits.settings.groups.institution import InstitutionSettings

__all__ = ["essential_data", "reference_fresh_scope", "reference_private_storage", "set_institution_settings"]


@pytest.fixture(autouse=True)
def reference_fresh_scope() -> Iterator[None]:
    """Settings are cached in Redis and permissions per scope: start every test clean."""
    cache.clear()
    begin_scope()
    yield
    begin_scope()
    cache.clear()
    # Requests activate the user's language in the thread; do not leak it into the next test.
    translation.deactivate()


@pytest.fixture(autouse=True)
def reference_private_storage(tmp_path: Any, settings: Any) -> None:
    """Uploaded CSV files and generated files go to a temporary private storage."""
    settings.STORAGES = {
        **settings.STORAGES,
        "default": {**settings.STORAGES["default"], "OPTIONS": {"location": str(tmp_path / "private")}},
    }


@pytest.fixture
def set_institution_settings(db: None) -> Callable[..., None]:
    def set_values(**values: Any) -> None:
        settings = InstitutionSettings.load()
        for name, value in values.items():
            setattr(settings, name, value)
        settings.save()

    return set_values


@pytest.fixture
def essential_data(db: None) -> None:
    """Original ``$this->seed(EssentialSeeder::class)``."""
    from ninefruits.setup.seeders.essential import EssentialSeeder

    EssentialSeeder()()
