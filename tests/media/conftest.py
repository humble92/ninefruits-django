from collections.abc import Iterator
from typing import Any

import pytest

from ninefruits.core import context
from tests.audit.support import grants


@pytest.fixture(autouse=True)
def _fresh_request_context() -> Iterator[None]:
    """A sign-in outside a request (``client.force_login``) updates the process-wide request
    context; start every test without a user."""
    context.clear()
    yield
    context.clear()


@pytest.fixture
def grant(monkeypatch: pytest.MonkeyPatch) -> Iterator[Any]:
    with grants(monkeypatch) as grant:
        yield grant
