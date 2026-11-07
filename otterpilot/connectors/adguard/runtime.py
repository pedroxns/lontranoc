from __future__ import annotations

from typing import Any

from otterpilot.capabilities.dns.providers.adguard import (
    collect as collect_dns,
    publish as publish_dns,
)


class AdGuardConnectorRuntime:
    connector_id = "adguard"

    def collect(
        self,
        capability_id: str,
    ) -> Any:
        if capability_id == "dns":
            return collect_dns()

        raise ValueError(
            f"Capability não suportada pelo Connector "
            f"{self.connector_id}: {capability_id}"
        )

    def publish(
        self,
        capability_id: str,
        payload: Any,
    ) -> None:
        if capability_id == "dns":
            publish_dns(payload)
            return

        raise ValueError(
            f"Capability não suportada pelo Connector "
            f"{self.connector_id}: {capability_id}"
        )
