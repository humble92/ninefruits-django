"""Driver -> connector (original ``ConnectorRegistry``).

Drivers come from :data:`ConnectorRegistry.DRIVERS` (the ``null`` driver), the optional
``LMS_CONNECTORS`` setting (``{"moodle": "myuniversity.lms.MoodleConnector"}``, dotted paths of
classes or factories) and :meth:`ConnectorRegistry.register` (an app's ``ready()``). A platform
on a driver without a connector fails loudly at sync time instead of silently doing nothing.
Tests replace a connector with :meth:`ConnectorRegistry.override`::

    with connectors().override("null", FakeConnector()):
        ...
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.utils.module_loading import import_string

from .base import LmsConnector

if TYPE_CHECKING:
    from ninefruits.lms.models import LmsPlatform

ConnectorFactory = Callable[[], LmsConnector]


class NoConnectorError(RuntimeError):
    """The platform's driver has no connector."""


class ConnectorRegistry:
    DRIVERS: ClassVar[dict[str, str]] = {"null": "ninefruits.lms.connectors.null.NullConnector"}

    def __init__(self) -> None:
        self._factories: dict[str, ConnectorFactory | str] = {}
        self._overrides: dict[str, LmsConnector] = {}

    def _all(self) -> dict[str, ConnectorFactory | str]:
        configured: dict[str, Any] = getattr(settings, "LMS_CONNECTORS", None) or {}
        return {**self.DRIVERS, **configured, **self._factories}

    def register(self, driver: str, factory: ConnectorFactory | str) -> None:
        """Adds or replaces the connector of a driver (a class, a factory or a dotted path)."""
        self._factories[driver] = factory

    def is_implemented(self, driver: str) -> bool:
        return driver in self._overrides or driver in self._all()

    def for_platform(self, platform: LmsPlatform) -> LmsConnector:
        driver = str(platform.driver)
        if driver in self._overrides:
            return self._overrides[driver]
        factory = self._all().get(driver)
        if factory is None:
            raise NoConnectorError(f"No connector for LMS driver [{driver}].")
        if isinstance(factory, str):
            factory = import_string(factory)
        return factory()

    @contextmanager
    def override(self, driver: str, connector: LmsConnector) -> Iterator[LmsConnector]:
        """Uses ``connector`` for the driver inside the block (test doubles)."""
        previous = self._overrides.get(driver)
        self._overrides[driver] = connector
        try:
            yield connector
        finally:
            if previous is None:
                self._overrides.pop(driver, None)
            else:
                self._overrides[driver] = previous


_registry = ConnectorRegistry()


def connectors() -> ConnectorRegistry:
    return _registry
