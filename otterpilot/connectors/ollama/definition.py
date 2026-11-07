from otterpilot.core.registry import (
    ComponentStatus,
    ConnectorDefinition,
    SettingDefinition,
)


OLLAMA_CONNECTOR = ConnectorDefinition(
    connector_id="ollama",
    display_name="Ollama",
    description=(
        "Runtime do Ollama: modelo carregado e latência. Também atende o Copilot."
    ),
    capabilities=("llm_runtime",),
    status=ComponentStatus.ENABLED,
    read_only_default=True,
    supports_discovery=True,
    settings=(
        SettingDefinition(
            key="OLLAMA_URL", label="URL", kind="url", required=True,
            help="Ex.: http://192.168.1.50:11434. Também usado pelo Copilot.",
        ),
        SettingDefinition(
            key="OLLAMA_MODEL", label="Modelo", default="qwen3.5:9b",
        ),
        SettingDefinition(
            key="OLLAMA_NUM_CTX", label="Janela de contexto (tokens)", kind="int",
            group="Copilot",
            help="Opcional. Vazio usa o padrão do Ollama.",
        ),
        SettingDefinition(
            key="OLLAMA_TIMEOUT_SECONDS", label="Timeout da resposta (s)", kind="int",
            default="120", group="Copilot",
        ),
    ),
    push_components=("copilot-mqtt",),
)
