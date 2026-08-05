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
from otterpilot.capabilities.host_health.definition import (
    HOST_HEALTH_CAPABILITY,
)
from otterpilot.capabilities.virtualization.definition import (
    VIRTUALIZATION_CAPABILITY,
)
from otterpilot.connectors.proxmox.definition import (
    PROXMOX_CONNECTOR,
)
from otterpilot.connectors.proxmox.runtime import (
    ProxmoxConnectorRuntime,
)
from otterpilot.core.registry import OtterPilotRegistry, registry
from otterpilot.capabilities.environment_health.definition import (
    ENVIRONMENT_HEALTH_CAPABILITY,
)
from otterpilot.capabilities.zigbee_health.definition import (
    ZIGBEE_HEALTH_CAPABILITY,
)
from otterpilot.connectors.zigbee2mqtt.definition import (
    ZIGBEE2MQTT_CONNECTOR,
)



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
            HOST_HEALTH_CAPABILITY,
            VIRTUALIZATION_CAPABILITY,
            ENVIRONMENT_HEALTH_CAPABILITY,
            ZIGBEE_HEALTH_CAPABILITY,
        )
    )

    registry.register_connectors(
        (
            HOMEASSISTANT_CONNECTOR,
            ADGUARD_CONNECTOR,
            FRIGATE_CONNECTOR,
            OLLAMA_CONNECTOR,
            PROXMOX_CONNECTOR,
            ZIGBEE2MQTT_CONNECTOR,
        )
    )

    return registry
