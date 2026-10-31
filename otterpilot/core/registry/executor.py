from __future__ import annotations

from typing import Any

from otterpilot.core.eventbus import INVENTORY_EVENT_TYPE, EventEnvelope
from otterpilot.core.registry.registry import OtterPilotRegistry
from otterpilot.core.registry.runtime import ConnectorRuntimeRegistry


class ConnectorExecutionError(RuntimeError):
    """Erro ao executar um Connector."""


class UnknownConnectorError(ConnectorExecutionError):
    """Connector não existe no catálogo declarativo."""


class UnsupportedCapabilityError(ConnectorExecutionError):
    """Connector não fornece a capability solicitada."""


class ConnectorExecutor:
    """Executa connectors validando metadados e runtime."""

    def __init__(
        self,
        metadata_registry: OtterPilotRegistry,
        runtime_registry: ConnectorRuntimeRegistry,
    ) -> None:
        self._metadata_registry = metadata_registry
        self._runtime_registry = runtime_registry

    def collect(
        self,
        connector_id: str,
        capability_id: str,
    ) -> Any:
        connector = self._metadata_registry.get_connector(connector_id)

        if connector is None:
            raise UnknownConnectorError(
                f"Connector não registrado: {connector_id}"
            )

        if capability_id not in connector.capabilities:
            raise UnsupportedCapabilityError(
                f"Connector {connector_id} não fornece "
                f"a capability {capability_id}"
            )

        runtime = self._runtime_registry.get(connector_id)

        return runtime.collect(capability_id)

    def publish(
        self,
        connector_id: str,
        capability_id: str,
        payload: Any,
    ) -> None:
        connector = self._metadata_registry.get_connector(connector_id)

        if connector is None:
            raise UnknownConnectorError(
                f"Connector não registrado: {connector_id}"
            )

        if capability_id not in connector.capabilities:
            raise UnsupportedCapabilityError(
                f"Connector {connector_id} não fornece "
                f"a capability {capability_id}"
            )

        runtime = self._runtime_registry.get(connector_id)
        runtime.publish(capability_id, payload)

    def collect_and_publish(
        self,
        connector_id: str,
        capability_id: str,
    ) -> Any:
        payload = self.collect(
            connector_id,
            capability_id,
        )

        if _is_inventory(payload):
            payload = [
                *payload,
                build_inventory_event(
                    connector_id,
                    capability_id,
                    payload,
                ),
            ]

        self.publish(
            connector_id,
            capability_id,
            payload,
        )

        return payload

def _is_inventory(payload: Any) -> bool:
    """Coletas que devolvem lista de envelopes trazem o inventário completo."""

    return isinstance(payload, list) and all(
        isinstance(item, EventEnvelope)
        for item in payload
    )


def build_inventory_event(
    connector_id: str,
    capability_id: str,
    events: list[EventEnvelope],
) -> EventEnvelope:
    resource_ids = sorted(
        {
            event.resource_id
            for event in events
            if event.resource_id
            and event.connector == connector_id
            and event.capability == capability_id
        }
    )

    return EventEnvelope(
        capability=capability_id,
        connector=connector_id,
        event_type=INVENTORY_EVENT_TYPE,
        message=f"Inventário de {connector_id}/{capability_id}",
        payload={"resource_ids": resource_ids},
    )
