from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
)


ZIGBEE2MQTT_CONNECTOR = ConnectorDefinition(
    connector_id="zigbee2mqtt",
    display_name="Zigbee2MQTT",
    description=(
        "Connects Zigbee2MQTT bridge, coordinator and "
        "network health to OtterPilot."
    ),
    capabilities=(
        "zigbee_health",
    ),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=True,
)
