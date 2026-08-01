from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
)


FRIGATE_CONNECTOR = ConnectorDefinition(
    connector_id="frigate",
    display_name="Frigate",
    description=(
        "Connects Frigate events, detections and camera health."
    ),
    capabilities=(
        "object_detection",
        "camera_health",
    ),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=True,
)
