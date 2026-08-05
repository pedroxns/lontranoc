from otterpilot.core.registry import CapabilityDefinition


ENVIRONMENT_HEALTH_CAPABILITY = CapabilityDefinition(
    capability_id="environment_health",
    display_name="Environment Health",
    domain="infrastructure",
    description=(
        "Environmental conditions affecting infrastructure, "
        "including temperature and related physical health signals."
    ),
)
