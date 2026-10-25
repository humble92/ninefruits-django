"""Platform connectors (ADR 0017). The registry maps drivers to connector classes."""

from .base import LmsConnector, PlatformCourse
from .null import NullConnector
from .registry import ConnectorRegistry, NoConnectorError, connectors

__all__ = ["ConnectorRegistry", "LmsConnector", "NoConnectorError", "NullConnector", "PlatformCourse", "connectors"]
