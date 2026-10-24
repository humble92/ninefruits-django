from __future__ import annotations

from collections.abc import Iterator

import pytest
from django.core.cache import cache
from django.utils import translation


@pytest.fixture(autouse=True)
def _fresh_settings_cache() -> Iterator[None]:
    """Settings groups are cached; tests that change them must not leak into others."""
    cache.clear()
    yield
    cache.clear()
    translation.activate("en")
