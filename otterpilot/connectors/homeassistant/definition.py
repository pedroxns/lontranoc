from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
)


HOMEASSISTANT_CONNECTOR = ConnectorDefinition(
    connector_id="homeassistant",
    display_name="Home Assistant",
    description=(
        "Connects Home Assistant entities and services to OtterPilot."
    ),
    capabilities=("vehicle",),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=True,
)
