from otterpilot.core.registry import CapabilityDefinition


SYSTEM_HEALTH_CAPABILITY = CapabilityDefinition(
    capability_id="system_health",
    display_name="System Health",
    domain="infrastructure",
    description=(
        "Consolidated operational health of resources "
        "monitored by OtterPilot."
    ),
)