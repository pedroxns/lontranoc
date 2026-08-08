from otterpilot.core.registry import CapabilityDefinition


DNS_CAPABILITY = CapabilityDefinition(
    capability_id="dns",
    display_name="DNS",
    domain="infrastructure",
    description=(
        "DNS resolution, filtering, service health and query activity."
    ),
)
