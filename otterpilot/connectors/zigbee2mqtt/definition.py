from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
    SettingDefinition,
)


ZIGBEE2MQTT_CONNECTOR = ConnectorDefinition(
    connector_id="zigbee2mqtt",
    display_name="Zigbee2MQTT",
    description=(
        "Bridge, coordenador e rede das instâncias Zigbee2MQTT."
    ),
    capabilities=(
        "zigbee_health",
    ),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=True,
    settings=(
        SettingDefinition(
            key="ZIGBEE2MQTT_BASE_TOPICS", label="Base topics", kind="list",
            default="zigbee2mqtt",
            help="Separados por vírgula, um por instância (ex.: z2m1,z2m2).",
        ),
    ),
    push_components=("zigbee2mqtt",),
)
