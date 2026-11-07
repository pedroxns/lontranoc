from otterpilot.core.registry import CapabilityDefinition


LLM_RUNTIME_CAPABILITY = CapabilityDefinition(
    capability_id="llm_runtime",
    display_name="LLM Runtime",
    domain="ai",
    description=(
        "Disponibilidade do runtime de LLM, modelos carregados e latência de inferência."
    ),
)
