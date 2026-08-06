from __future__ import annotations

from typing import Any

from otterpilot.capabilities.system_health.providers.otterpilot import (
    collect as collect_system_health,
    publish as publish_system_health,
)


class OtterPilotConnectorRuntime:
    connector_id = "otterpilot"

    def collect(
        self,
        capability_id: str,
    ) -> Any:
        if capability_id == "system_health":
            return collect_system_health()

        raise ValueError(
            f"Capability não suportada pelo Connector "
            f"{self.connector_id}: {capability_id}"
        )

    def publish(
        self,
        capability_id: str,
        payload: Any,
    ) -> None:
        if capability_id == "system_health":
            publish_system_health(payload)
            return

        raise ValueError(
            f"Capability não suportada pelo Connector "
            f"{self.connector_id}: {capability_id}"
        )
