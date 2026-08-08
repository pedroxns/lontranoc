from otterpilot.core.registry import CapabilityDefinition


ZIGBEE_HEALTH_CAPABILITY = CapabilityDefinition(
    capability_id="zigbee_health",
    display_name="Zigbee Health",
    domain="infrastructure",
    description=(
        "Zigbee coordinator, bridge, MQTT connectivity, "
        "device activity and network health."
    ),
)
