from otterpilot.core.registry import CapabilityDefinition


CAMERA_HEALTH_CAPABILITY = CapabilityDefinition(
    capability_id="camera_health",
    display_name="Camera Health",
    domain="security",
    description=(
        "Camera availability, streams, capture failures and transport health."
    ),
)
