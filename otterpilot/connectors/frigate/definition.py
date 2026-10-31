from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
    SettingDefinition,
)


FRIGATE_CONNECTOR = ConnectorDefinition(
    connector_id="frigate",
    display_name="Frigate",
    description=(
        "Saúde das câmeras e detecções do Frigate NVR."
    ),
    capabilities=(
        "object_detection",
        "camera_health",
    ),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=True,
    settings=(
        SettingDefinition(
            key="FRIGATE_URL", label="URL da API", kind="url", required=True,
            help="Ex.: http://frigate.local:5000 (saúde das câmeras).",
        ),
        SettingDefinition(
            key="FRIGATE_MQTT_PREFIX", label="Prefixo MQTT", default="frigate",
            help="Detecções chegam pelo broker MQTT configurado no sistema.",
        ),
    ),
    push_components=("frigate-mqtt",),
)
