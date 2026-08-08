from otterpilot.core.registry import CapabilityDefinition


VEHICLE_CAPABILITY = CapabilityDefinition(
    capability_id="vehicle",
    display_name="Vehicle",
    domain="mobility",
    description=(
        "Vehicle state, location, energy, tires, access and maintenance."
    ),
    aliases=(
        "car",
        "automobile",
    ),
)
