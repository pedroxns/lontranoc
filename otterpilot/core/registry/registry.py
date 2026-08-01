from __future__ import annotations

from collections.abc import Iterable

from otterpilot.core.registry.models import (
    CapabilityDefinition,
    ConnectorDefinition,
)


class RegistryError(RuntimeError):
    """Erro relacionado ao catálogo de componentes do OtterPilot."""


class DuplicateRegistrationError(RegistryError):
    """Um identificador já existe no Registry."""


class UnknownCapabilityError(RegistryError):
    """Um Connector declarou uma capability inexistente."""


class OtterPilotRegistry:
    """Catálogo de capabilities e connectors disponíveis."""

    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilityDefinition] = {}
        self._connectors: dict[str, ConnectorDefinition] = {}

    def register_capability(
        self,
        capability: CapabilityDefinition,
    ) -> None:
        if capability.capability_id in self._capabilities:
            raise DuplicateRegistrationError(
                f"Capability já registrada: {capability.capability_id}"
            )

        self._capabilities[capability.capability_id] = capability

    def register_connector(
        self,
        connector: ConnectorDefinition,
    ) -> None:
        if connector.connector_id in self._connectors:
            raise DuplicateRegistrationError(
                f"Connector já registrado: {connector.connector_id}"
            )

        unknown = [
            capability_id
            for capability_id in connector.capabilities
            if capability_id not in self._capabilities
        ]

        if unknown:
            raise UnknownCapabilityError(
                f"Connector {connector.connector_id} declarou "
                f"capabilities desconhecidas: {', '.join(unknown)}"
            )

        self._connectors[connector.connector_id] = connector

    def get_capability(
        self,
        capability_id: str,
    ) -> CapabilityDefinition | None:
        return self._capabilities.get(capability_id)

    def get_connector(
        self,
        connector_id: str,
    ) -> ConnectorDefinition | None:
        return self._connectors.get(connector_id)

    def list_capabilities(self) -> tuple[CapabilityDefinition, ...]:
        return tuple(
            sorted(
                self._capabilities.values(),
                key=lambda item: item.capability_id,
            )
        )

    def list_connectors(self) -> tuple[ConnectorDefinition, ...]:
        return tuple(
            sorted(
                self._connectors.values(),
                key=lambda item: item.connector_id,
            )
        )

    def connectors_for_capability(
        self,
        capability_id: str,
    ) -> tuple[ConnectorDefinition, ...]:
        return tuple(
            connector
            for connector in self.list_connectors()
            if capability_id in connector.capabilities
        )

    def register_capabilities(
        self,
        capabilities: Iterable[CapabilityDefinition],
    ) -> None:
        for capability in capabilities:
            self.register_capability(capability)

    def register_connectors(
        self,
        connectors: Iterable[ConnectorDefinition],
    ) -> None:
        for connector in connectors:
            self.register_connector(connector)


registry = OtterPilotRegistry()
