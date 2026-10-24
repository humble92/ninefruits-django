"""pytest hook (called from tests/conftest.py): compiles the gettext catalogs
whose ``.mo`` is older than the ``.po`` before the tests run (``.mo`` files are not in git)."""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    from ninefruits.i18n.catalogs import compile_project_catalogs

    compile_project_catalogs(Path(__file__).resolve().parents[2])
