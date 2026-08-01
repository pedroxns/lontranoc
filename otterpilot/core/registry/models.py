from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ComponentStatus(StrEnum):
    AVAILABLE = "available"
    ENABLED = "enabled"
    DISABLED = "disabled"
    DEGRADED = "degraded"
    ERROR = "error"


class CapabilityDefinition(BaseModel):
    """Declara uma capability compreendida pelo OtterPilot."""

    model_config = ConfigDict(frozen=True)

    capability_id: str = Field(
        min_length=1,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    display_name: str
    domain: str
    description: str = ""
    version: str = "1.0"
    aliases: tuple[str, ...] = ()
    cross_domains: tuple[str, ...] = ()


class ConnectorDefinition(BaseModel):
    """Declara um produto externo conectado ao OtterPilot."""

    model_config = ConfigDict(frozen=True)

    connector_id: str = Field(
        min_length=1,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    display_name: str
    description: str = ""
    version: str = "1.0"
    capabilities: tuple[str, ...] = ()
    status: ComponentStatus = ComponentStatus.AVAILABLE
    read_only_default: bool = True
    supports_discovery: bool = False
