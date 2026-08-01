from otterpilot.core.registry import CapabilityDefinition


OBJECT_DETECTION_CAPABILITY = CapabilityDefinition(
    capability_id="object_detection",
    display_name="Object Detection",
    domain="security",
    description=(
        "Detection events, labels, confidence and observed entities."
    ),
)
