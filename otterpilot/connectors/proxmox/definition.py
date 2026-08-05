from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
)


PROXMOX_CONNECTOR = ConnectorDefinition(
    connector_id="proxmox",
    display_name="Proxmox VE",
    description=(
        "Connects Proxmox VE nodes and virtualization resources "
        "to OtterPilot."
    ),
    capabilities=(
        "host_health",
        "virtualization",
    ),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=True,
)
