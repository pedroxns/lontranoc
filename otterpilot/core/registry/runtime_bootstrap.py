from __future__ import annotations

from otterpilot.connectors.frigate.runtime import (
    FrigateConnectorRuntime,
)
from otterpilot.connectors.homeassistant.runtime import (
    HomeAssistantConnectorRuntime,
)
from otterpilot.core.registry.runtime import (
    ConnectorRuntimeRegistry,
)
from otterpilot.connectors.adguard.runtime import (
    AdGuardConnectorRuntime,
)


def build_default_runtime_registry() -> ConnectorRuntimeRegistry:
    registry = ConnectorRuntimeRegistry()

    registry.register(
        HomeAssistantConnectorRuntime()
    )

    registry.register(
        FrigateConnectorRuntime()
    )
    registry.register(
    	AdGuardConnectorRuntime()
    )

    return registry
