from __future__ import annotations

from otterpilot.connectors.adguard.runtime import (
    AdGuardConnectorRuntime,
)
from otterpilot.connectors.frigate.runtime import (
    FrigateConnectorRuntime,
)
from otterpilot.connectors.homeassistant.runtime import (
    HomeAssistantConnectorRuntime,
)
from otterpilot.connectors.ollama.runtime import (
    OllamaConnectorRuntime,
)
from otterpilot.connectors.proxmox.runtime import (
    ProxmoxConnectorRuntime,
)
from otterpilot.core.registry.runtime import (
    ConnectorRuntimeRegistry,
)
from otterpilot.connectors.otterpilot.runtime import (
    OtterPilotConnectorRuntime,
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

    registry.register(
        OllamaConnectorRuntime()
    )

    registry.register(
        ProxmoxConnectorRuntime()
    )

    registry.register(
        OtterPilotConnectorRuntime()
    )

    return registry