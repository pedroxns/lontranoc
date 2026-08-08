from __future__ import annotations

from typing import Any

from otterpilot.capabilities.host_health.providers.proxmox import (
    collect as collect_host_health,
    publish as publish_host_health,
)
from otterpilot.capabilities.virtualization.providers.proxmox import (
    collect as collect_virtualization,
    publish as publish_virtualization,
)


class ProxmoxConnectorRuntime:
    connector_id = "proxmox"

    def collect(
        self,
        capability_id: str,
    ) -> Any:
        if capability_id == "host_health":
            return collect_host_health()
        elif capability_id == "virtualization":
            return collect_virtualization()

        raise ValueError(
            f"Capability não suportada pelo Connector "
            f"{self.connector_id}: {capability_id}"
        )

    def publish(
        self,
        capability_id: str,
        payload: Any,
    ) -> None:
        if capability_id == "host_health":
            publish_host_health(payload)
            return
        elif capability_id == "virtualization":
            publish_virtualization(payload)
            return

        raise ValueError(
            f"Capability não suportada pelo Connector "
            f"{self.connector_id}: {capability_id}"
        )
