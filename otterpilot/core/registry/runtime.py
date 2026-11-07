from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ConnectorRuntime(Protocol):
    """Contrato mínimo para runtimes executáveis de connectors."""

    connector_id: str

    def collect(
        self,
        capability_id: str,
    ) -> Any:
        """Coleta dados normalizados de uma capability."""

    def publish(
        self,
        capability_id: str,
        payload: Any,
    ) -> None:
        """Publica os dados coletados no fluxo de conhecimento."""


class RuntimeRegistryError(RuntimeError):
    """Erro relacionado ao catálogo de runtimes."""


class DuplicateRuntimeError(RuntimeRegistryError):
    """Um runtime já está registrado para o connector."""


class UnknownRuntimeError(RuntimeRegistryError):
    """Não existe runtime registrado para o connector."""


class ConnectorRuntimeRegistry:
    """Associa identificadores de connectors a runtimes executáveis."""

    def __init__(self) -> None:
        self._runtimes: dict[str, ConnectorRuntime] = {}

    def register(
        self,
        runtime: ConnectorRuntime,
    ) -> None:
        connector_id = runtime.connector_id

        if connector_id in self._runtimes:
            raise DuplicateRuntimeError(
                f"Runtime já registrado para: {connector_id}"
            )

        if not isinstance(runtime, ConnectorRuntime):
            raise TypeError(
                f"Runtime inválido para o connector: {connector_id}"
            )

        self._runtimes[connector_id] = runtime

    def get(
        self,
        connector_id: str,
    ) -> ConnectorRuntime:
        runtime = self._runtimes.get(connector_id)

        if runtime is None:
            raise UnknownRuntimeError(
                f"Runtime não registrado para: {connector_id}"
            )

        return runtime

    def list_connector_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._runtimes))


runtime_registry = ConnectorRuntimeRegistry()
