from otterpilot.core.registry import CapabilityDefinition


LLM_RUNTIME_CAPABILITY = CapabilityDefinition(
    capability_id="llm_runtime",
    display_name="LLM Runtime",
    domain="ai",
    description=(
        "LLM runtime availability, loaded models, inference latency "
        "and accelerator telemetry."
    ),
)
