from __future__ import annotations

from typing import Any

from otterpilot.capabilities.vehicle.providers.homeassistant import (
    collect as collect_vehicle,
    publish as publish_vehicle,
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

        raise ValueError(
            f"Capability não suportada pelo Connector "
            f"{self.connector_id}: {capability_id}"
        )
