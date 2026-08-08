from otterpilot.core.registry import CapabilityDefinition


UPS_CAPABILITY = CapabilityDefinition(
    capability_id="ups",
    display_name="UPS",
    domain="infrastructure",
    description=(
        "Uninterruptible power supply status, battery level, "
        "power state and runtime health."
    ),
    cross_domains=("energy",),
)
