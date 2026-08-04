from __future__ import annotations

from otterpilot.capabilities.camera_health.definition import (
    CAMERA_HEALTH_CAPABILITY,
)
from otterpilot.capabilities.dns.definition import DNS_CAPABILITY
from otterpilot.capabilities.object_detection.definition import (
    OBJECT_DETECTION_CAPABILITY,
)
from otterpilot.capabilities.ups.definition import UPS_CAPABILITY
from otterpilot.capabilities.vehicle.definition import VEHICLE_CAPABILITY
from otterpilot.connectors.adguard.definition import ADGUARD_CONNECTOR
from otterpilot.connectors.frigate.definition import FRIGATE_CONNECTOR
from otterpilot.connectors.homeassistant.definition import (
    HOMEASSISTANT_CONNECTOR,
)
from otterpilot.capabilities.llm_runtime.definition import (
    LLM_RUNTIME_CAPABILITY,
)
from otterpilot.connectors.ollama.definition import (
    OLLAMA_CONNECTOR,
)
from otterpilot.core.registry import OtterPilotRegistry, registry



def build_default_registry() -> OtterPilotRegistry:
    registry = OtterPilotRegistry()

    registry.register_capabilities(
        (
            VEHICLE_CAPABILITY,
            DNS_CAPABILITY,
            OBJECT_DETECTION_CAPABILITY,
            CAMERA_HEALTH_CAPABILITY,
            LLM_RUNTIME_CAPABILITY,
            UPS_CAPABILITY,
        )
    )

    registry.register_connectors(
        (
            HOMEASSISTANT_CONNECTOR,
            ADGUARD_CONNECTOR,
            FRIGATE_CONNECTOR,
            OLLAMA_CONNECTOR,
        )
    )

    return registry
