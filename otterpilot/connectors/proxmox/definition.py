from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
    SettingDefinition,
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
    settings=(
        SettingDefinition(
            key="PROXMOX_URL", label="URL", kind="url", required=True,
            help="Ex.: https://192.168.1.2:8006",
        ),
        SettingDefinition(
            key="PROXMOX_VERIFY_SSL", label="Validar certificado TLS", kind="bool",
            default="true",
        ),
        SettingDefinition(
            key="PROXMOX_TOKEN_ID", label="Token ID", required=True,
            credential="proxmox_token_id",
            help="Formato usuario@realm!token. Permissão PVEAuditor basta.",
        ),
        SettingDefinition(
            key="PROXMOX_TOKEN_SECRET", label="Token secret", kind="secret",
            required=True, credential="proxmox_token_secret",
        ),
    ),
)
