from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
)


OLLAMA_CONNECTOR = ConnectorDefinition(
    connector_id="ollama",
    display_name="Ollama",
    description=(
        "Connects Ollama runtime, model and accelerator telemetry."
    ),
    capabilities=("llm_runtime",),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=True,
)
