from __future__ import annotations

from typing import Any

from otterpilot.capabilities.vehicle.providers.homeassistant import (
    collect as collect_vehicle,
    publish as publish_vehicle,
)
from otterpilot.capabilities.ups.providers.homeassistant import (
    collect as collect_ups,
    publish as publish_ups,
)


class HomeAssistantConnectorRuntime:
    """Implementação executável do Connector Home Assistant."""

    connector_id = "homeassistant"

    def collect(
        self,
        capability_id: str,
    ) -> dict[str, Any]:
        if capability_id == "vehicle":
            return collect_vehicle()
        if capability_id == "ups":
            return collect_ups()

        raise ValueError(
            f"Capability não suportada pelo Connector "
            f"{self.connector_id}: {capability_id}"
        )

    def publish(
        self,
        capability_id: str,
        payload: dict[str, Any],
    ) -> None:
        if capability_id == "vehicle":
            publish_vehicle(payload)
            return
        if capability_id == "ups":
            publish_ups(payload)
            return

        raise ValueError(
            f"Capability não suportada pelo Connector "
            f"{self.connector_id}: {capability_id}"
        )
