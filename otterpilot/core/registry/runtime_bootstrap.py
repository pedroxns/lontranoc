from __future__ import annotations

from otterpilot.connectors.homeassistant.runtime import (
    HomeAssistantConnectorRuntime,
)
from otterpilot.core.registry.runtime import (
    ConnectorRuntimeRegistry,
)


def build_default_runtime_registry() -> ConnectorRuntimeRegistry:
    registry = ConnectorRuntimeRegistry()

    registry.register(
        HomeAssistantConnectorRuntime()
    )

    return registry
