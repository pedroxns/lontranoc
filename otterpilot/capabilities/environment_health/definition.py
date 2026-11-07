from otterpilot.core.registry import CapabilityDefinition


ENVIRONMENT_HEALTH_CAPABILITY = CapabilityDefinition(
    capability_id="environment_health",
    display_name="Environment Health",
    domain="infrastructure",
    description=(
        "Condições ambientais que afetam a infraestrutura, como a temperatura do rack."
    ),
)
