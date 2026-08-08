from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
)


ADGUARD_CONNECTOR = ConnectorDefinition(
    connector_id="adguard",
    display_name="AdGuard Home",
    description=(
        "Connects AdGuard Home DNS health and filtering data."
    ),
    capabilities=("dns",),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=True,
)
