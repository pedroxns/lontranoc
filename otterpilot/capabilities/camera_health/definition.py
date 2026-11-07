from otterpilot.core.registry import CapabilityDefinition


CAMERA_HEALTH_CAPABILITY = CapabilityDefinition(
    capability_id="camera_health",
    display_name="Camera Health",
    domain="security",
    description=(
        "Disponibilidade das câmeras, streams e falhas de captura."
    ),
)
