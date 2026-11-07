from __future__ import annotations

from typing import Any

from otterpilot.integrations.frigate.health_provider import (
    collect as collect_camera_health,
    publish as publish_camera_health,
)


class FrigateConnectorRuntime:
    connector_id = "frigate"

    def collect(
        self,
        capability_id: str,
    ) -> Any:
        if capability_id == "camera_health":
            return collect_camera_health()

        raise ValueError(
            f"Capability não disponível via polling no "
            f"Connector {self.connector_id}: {capability_id}"
        )

    def publish(
        self,
        capability_id: str,
        payload: Any,
    ) -> None:
        if capability_id == "camera_health":
            publish_camera_health(payload)
            return

        raise ValueError(
            f"Capability não disponível via polling no "
            f"Connector {self.connector_id}: {capability_id}"
        )
