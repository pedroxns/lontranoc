from otterpilot.core.registry import CapabilityDefinition


VIRTUALIZATION_CAPABILITY = CapabilityDefinition(
    capability_id="virtualization",
    display_name="Virtualization",
    domain="infrastructure",
    description=(
        "Clusters, nós, máquinas virtuais e containers do hypervisor."
    ),
)
