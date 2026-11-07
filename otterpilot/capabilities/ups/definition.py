from otterpilot.core.registry import CapabilityDefinition


UPS_CAPABILITY = CapabilityDefinition(
    capability_id="ups",
    display_name="UPS",
    domain="infrastructure",
    description=(
        "Status do nobreak, nível de bateria e alimentação."
    ),
    cross_domains=("energy",),
)
