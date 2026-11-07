from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
    SettingDefinition,
)


HOMEASSISTANT_CONNECTOR = ConnectorDefinition(
    connector_id="homeassistant",
    display_name="Home Assistant",
    description=(
        "Entidades do Home Assistant: UPS, temperatura do rack e veículo."
    ),
    capabilities=(
    "vehicle",
    "ups",
    "environment_health",
    ),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=True,
    settings=(
        SettingDefinition(
            key="HA_URL", label="URL", kind="url", required=True,
            help="Ex.: http://homeassistant.local:8123",
        ),
        SettingDefinition(
            key="HA_TOKEN", label="Token de acesso", kind="secret", required=True,
            help="Long-lived access token do usuário do Home Assistant.",
        ),
        SettingDefinition(
            key="UPS_STATUS_ENTITY", label="Entidade de status", group="UPS",
            help="Ex.: sensor.nobreak_status",
        ),
        SettingDefinition(
            key="UPS_BATTERY_ENTITY", label="Entidade de bateria (%)", group="UPS",
        ),
        SettingDefinition(
            key="RACK_TEMP_ENTITY", label="Entidade de temperatura", group="Ambiente",
        ),
        SettingDefinition(
            key="HA_TOKEN_VEHICLE", label="Token alternativo", kind="secret",
            group="Veículo",
            help="Opcional. O mapeamento de entidades fica em vehicle.yaml.",
        ),
    ),
)
