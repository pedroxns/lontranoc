from otterpilot.core.registry import CapabilityDefinition


OBJECT_DETECTION_CAPABILITY = CapabilityDefinition(
    capability_id="object_detection",
    display_name="Object Detection",
    domain="security",
    description=(
        "Eventos de detecção, rótulos, confiança e entidades observadas."
    ),
)
