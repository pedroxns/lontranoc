from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
)


OTTERPILOT_CONNECTOR = ConnectorDefinition(
    connector_id="otterpilot",
    display_name="OtterPilot",
    description=(
        "Internal OtterPilot services and consolidated "
        "system health."
    ),
    capabilities=(
        "system_health",
    ),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=False,
)
