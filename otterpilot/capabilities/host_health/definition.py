from otterpilot.core.registry import CapabilityDefinition


HOST_HEALTH_CAPABILITY = CapabilityDefinition(
    capability_id="host_health",
    display_name="Host Health",
    domain="infrastructure",
    description=(
        "Host availability, CPU, memory, storage, uptime "
        "and operating health."
    ),
)
