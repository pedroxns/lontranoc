from otterpilot.core.registry import CapabilityDefinition


VEHICLE_CAPABILITY = CapabilityDefinition(
    capability_id="vehicle",
    display_name="Vehicle",
    domain="mobility",
    description=(
        "Estado do veículo: localização, energia, pneus, acesso e manutenção."
    ),
    aliases=(
        "car",
        "automobile",
    ),
)
