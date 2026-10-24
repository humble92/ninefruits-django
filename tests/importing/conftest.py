from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.reference_conftest import *  # noqa: F403


@pytest.fixture
def csv_file(tmp_path: Path) -> Callable[[str, list[list[str]]], str]:
    """Original ``csvFile($directory, $name, $rows)``."""

    def write(name: str, rows: list[list[str]]) -> str:
        path = tmp_path / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows(rows)
        return str(path)

    return write


@pytest.fixture
def reference_data(essential_data: None) -> None:
    from ninefruits.setup.seeders.profiles.korean_university import KoreanUniversityProfileSeeder

    KoreanUniversityProfileSeeder()()
