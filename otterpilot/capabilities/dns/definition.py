from otterpilot.core.registry import CapabilityDefinition


DNS_CAPABILITY = CapabilityDefinition(
    capability_id="dns",
    display_name="DNS",
    domain="infrastructure",
    description=(
        "Resolução DNS, filtragem, saúde do serviço e volume de consultas."
    ),
)
