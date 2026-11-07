from otterpilot.core.registry import CapabilityDefinition


ZIGBEE_HEALTH_CAPABILITY = CapabilityDefinition(
    capability_id="zigbee_health",
    display_name="Zigbee Health",
    domain="infrastructure",
    description=(
        "Coordenador Zigbee, bridge, conectividade MQTT e dispositivos."
    ),
)
