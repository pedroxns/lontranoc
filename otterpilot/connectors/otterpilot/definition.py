from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
)


OTTERPILOT_CONNECTOR = ConnectorDefinition(
    connector_id="otterpilot",
    display_name="OtterPilot",
    description=(
        "Serviços internos e saúde consolidada do OtterPilot."
    ),
    capabilities=(
        "system_health",
    ),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=False,
)
