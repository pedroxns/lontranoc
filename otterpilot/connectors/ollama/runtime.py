from __future__ import annotations

from typing import Any

from otterpilot.integrations.ollama.status_provider import (
    collect as collect_llm_runtime,
    publish as publish_llm_runtime,
)


class OllamaConnectorRuntime:
    connector_id = "ollama"

    def collect(
        self,
        capability_id: str,
    ) -> Any:
        if capability_id == "llm_runtime":
            return collect_llm_runtime()

        raise ValueError(
            f"Capability não suportada pelo Connector "
            f"{self.connector_id}: {capability_id}"
        )

    def publish(
        self,
        capability_id: str,
        payload: Any,
    ) -> None:
        if capability_id == "llm_runtime":
            publish_llm_runtime(payload)
            return

        raise ValueError(
            f"Capability não suportada pelo Connector "
            f"{self.connector_id}: {capability_id}"
        )
