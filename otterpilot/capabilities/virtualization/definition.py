from otterpilot.core.registry import CapabilityDefinition


VIRTUALIZATION_CAPABILITY = CapabilityDefinition(
    capability_id="virtualization",
    display_name="Virtualization",
    domain="infrastructure",
    description=(
        "Hypervisor clusters, nodes, virtual machines, containers "
        "and virtualization workloads."
    ),
)
