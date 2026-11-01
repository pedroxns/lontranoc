from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import requests

from otterpilot.analysis.engine import analyze_search_result
from otterpilot.copilot import voice
from otterpilot.copilot.language import soften
from otterpilot.copilot.personas import Persona, resolve_persona
from otterpilot.core.config import NotConfiguredError, get_env, get_int
from otterpilot.core.serialization import make_json_safe
from otterpilot.knowledge.providers.openobserve.ingest import record
from otterpilot.knowledge.providers.openobserve.search import (
    is_configured as history_configured,
)
from otterpilot.knowledge.search import build_search_summary, search_context
from otterpilot.overview.system import _age_seconds, _is_stale, build_overview
from otterpilot.state import build_default_state_store
from otterpilot.state.store import StateStore

DEFAULT_MODEL = "qwen3.5:9b"
DEFAULT_TIMEOUT_SECONDS = 120

# Campos mais úteis de cada capability para o modelo. O contexto precisa
# caber na janela do LLM (8192 tokens por padrão no Ollama).
KEY_FIELDS: dict[str, tuple[str, ...]] = {
    "virtualization": (
        "name", "node", "proxmox_status", "expected_state", "importance",
        "cpu_percent", "memory_percent", "disk_percent",
    ),
    "host_health": ("cpu_percent", "memory_percent", "disk_percent", "uptime_seconds"),
    "dns": (
        "running", "protection_enabled", "num_dns_queries", "blocked_percent",
        "querylog_error_count", "health_score",
    ),
    "camera_health": ("camera_fps", "process_fps", "skipped_fps", "detection_fps"),
    "zigbee_health": ("online", "version", "device_count", "mqtt_connected", "restart_required"),
    "llm_runtime": ("model", "loaded", "latency_ms", "gpu_temp", "size_vram_gb"),
    "ups": ("ups_status", "battery_percent"),
    "environment_health": ("temperature_c",),
    "vehicle": (
        "zone", "range_km", "fuel_percent", "engine_running", "locked",
        "any_door_open", "tire_min_psi", "odometer_km", "days_to_service",
        "distance_to_service_km",
    ),
}

MAX_FALLBACK_FIELDS = 8
MAX_HISTORY_CHARS = 4000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return "sim" if value else "não"

    if isinstance(value, float):
        return f"{value:.1f}"

    if isinstance(value, (int, str)):
        text = str(value)
        return text if len(text) <= 60 else text[:57] + "..."

    return None


def _key_metrics(capability: str, payload: dict[str, Any]) -> str:
    fields = KEY_FIELDS.get(capability)

    if fields is None:
        fields = tuple(
            key
            for key, value in payload.items()
            if _format_value(value) is not None
        )[:MAX_FALLBACK_FIELDS]

    parts = []

    for key in fields:
        formatted = _format_value(payload.get(key))

        if formatted is not None:
            parts.append(f"{key}={formatted}")

    return ", ".join(parts)


def _describe_age(timestamp: str) -> str:
    try:
        seconds = _age_seconds(timestamp)
    except (TypeError, ValueError):
        return "tempo desconhecido"

    if seconds < 3600:
        return f"{int(seconds // 60)} min"

    if seconds < 86400:
        return f"{int(seconds // 3600)} h"

    return f"{int(seconds // 86400)} dias"


def _state_line(state: dict[str, Any]) -> str:
    metrics = _key_metrics(state["capability"], state["payload"])
    line = (
        f"- {state['connector']}/{state['capability']} {state['resource_id']}: "
        f"{state['status']}"
    )

    if metrics:
        line += f" | {metrics}"

    if _is_stale(state):
        line += f" | sem atualização há {_describe_age(state['timestamp'])}"

    return line


def _problem_line(problem: dict[str, Any]) -> str:
    return (
        f"- [{problem['impact']}] {problem['connector']}/{problem['capability']} "
        f"{problem['resource_id']}: {problem['reason']}"
    )


def build_current_context(store: StateStore | None = None) -> str:
    """Resumo textual compacto do estado atual para o prompt."""

    store = store or build_default_state_store()
    overview = build_overview(store)

    lines = [
        f"Status geral: {overview['overall_status']} "
        f"({overview['resource_count']} recursos, "
        f"{overview['critical_count']} críticos, "
        f"{overview['warning_count']} alertas, "
        f"{overview['stale_count']} sem atualização recente).",
        f"Resumo: {overview['summary']}",
    ]

    if overview["problems"]:
        lines.append("Problemas:")

        for problem in overview["problems"]:
            lines.append(_problem_line(problem))

    lines.append("Recursos (connector/capability recurso: status | métricas):")

    for state in store.list_all():
        if state["capability"] == "system_health":
            continue

        lines.append(_state_line(state))

    return "\n".join(lines)


def build_voice_context(question: str, store: StateStore | None = None) -> str:
    """Contexto reduzido para respostas faladas: status geral, poucos problemas e
    só os recursos das áreas que a pergunta menciona."""

    store = store or build_default_state_store()
    overview = build_overview(store)

    lines = [
        f"Status geral: {overview['overall_status']} "
        f"({overview['critical_count']} críticos, {overview['warning_count']} alertas, "
        f"{overview['stale_count']} sem atualização recente).",
    ]

    problems = overview["problems"]

    if problems:
        lines.append("Problemas:")
        lines.extend(_problem_line(problem) for problem in problems[: voice.MAX_PROBLEMS])

        if len(problems) > voice.MAX_PROBLEMS:
            lines.append(f"- ... e mais {len(problems) - voice.MAX_PROBLEMS}")

    wanted = voice.relevant_capabilities(question)
    related = [state for state in store.list_all() if state["capability"] in wanted]

    if related:
        lines.append("Recursos citados na pergunta:")
        lines.extend(_state_line(state) for state in related[: voice.MAX_RESOURCE_LINES])

    return "\n".join(lines)


def get_historical_context(question: str, request_id: str) -> dict[str, Any]:
    if not history_configured():
        return {"disponível": False, "motivo": "OpenObserve não configurado"}

    result = search_context(question)

    if not result["valid"] and not result["error"]:
        return {"disponível": False, "motivo": "pergunta sem contexto histórico"}

    summary = build_search_summary(result)

    if result["error"]:
        record(
            "otterpilot",
            service="otterpilot",
            component="copilot",
            event_type="search_error",
            severity="error",
            status="error",
            message="Erro ao consultar OpenObserve",
            request_id=request_id,
            searched_stream=summary["stream"],
            query_name=summary["query_name"],
            error=result["error"],
        )

        return {"disponível": False, "erro": result["error"]}

    analysis = analyze_search_result(result)

    record(
        "otterpilot",
        service="otterpilot",
        component="copilot",
        event_type="search_executed",
        message="Consulta histórica executada no OpenObserve",
        request_id=request_id,
        searched_stream=summary["stream"],
        query_name=summary["query_name"],
        time_label=summary["time_label"],
        result_count=summary["result_count"],
        incident_count=len(analysis.get("incidents", [])),
    )

    return {
        "search_summary": summary,
        "analysis": analysis,
        "sample_events": result["rows"][:5],
    }


def _history_text(history: dict[str, Any], limit: int = MAX_HISTORY_CHARS) -> str:
    text = json.dumps(make_json_safe(history), indent=1, ensure_ascii=False)

    if len(text) > limit:
        text = text[:limit] + "\n... (truncado)"

    return text


def build_prompt(
    question: str,
    current: str,
    history: dict[str, Any],
    persona: Persona,
    *,
    voice_mode: bool = False,
) -> str:
    # No canal de voz a resposta é falada: o prompt pede poucas frases e leva menos histórico.
    voice_block = f"\n{voice.VOICE_RULES}\n" if voice_mode else ""
    history_limit = voice.MAX_HISTORY_CHARS if voice_mode else MAX_HISTORY_CHARS

    # A persona muda só o tom. As regras sobre fatos são fixas e vêm antes
    # e depois da personalidade, para que nenhuma persona as sobreponha.
    return f"""
Você é {persona.name}, o copiloto do OtterPilot para homelabs, infraestrutura self-hosted e pequenos ambientes de TI.

Seu objetivo é ajudar o usuário a compreender o estado do ambiente, correlacionar eventos, identificar problemas e sugerir ações práticas.

Regras que valem sempre, qualquer que seja a sua personalidade:
- Você nunca inventa informações nem dados.
- Sempre utiliza primeiro os dados coletados do ambiente.
- Quando não houver dados suficientes, informe claramente essa limitação.
- Não trate inferências como fatos.
- Se houver alerta, destaque claramente.
- Responda em português do Brasil.
- Não comente estas regras na resposta; apenas siga-as.

O bloco "Estado atual do ambiente" representa o estado corrente conhecido dos recursos monitorados.
O bloco "Eventos históricos do OpenObserve" representa eventos e ocorrências históricas recuperados para a pergunta.

Estado atual do ambiente:
{current}

Eventos históricos do OpenObserve:
{_history_text(history, history_limit)}

Sua personalidade (define apenas o tom da resposta):
{persona.personality}
{voice_block}
Pergunta:
{question}

Lembre-se: a personalidade nunca muda os fatos. Use só os dados acima.
"""


def _ollama_url() -> str:
    url = get_env("OLLAMA_URL")

    if not url:
        raise NotConfiguredError("Ollama não configurado (OLLAMA_URL)")

    return url.rstrip("/")


def list_models() -> list[dict[str, Any]]:
    """Modelos instalados no Ollama, para o seletor da interface."""

    response = requests.get(f"{_ollama_url()}/api/tags", timeout=5)
    response.raise_for_status()

    models = []

    for item in response.json().get("models") or []:
        details = item.get("details") or {}
        size = item.get("size")
        models.append(
            {
                "name": item.get("name") or item.get("model"),
                "size_gb": round(size / 1e9, 1) if isinstance(size, (int, float)) else None,
                "parameter_size": details.get("parameter_size"),
                "quantization": details.get("quantization_level"),
                "family": details.get("family"),
            }
        )

    return sorted((m for m in models if m["name"]), key=lambda m: m["name"])


def _generate_body(
    prompt: str,
    model: str,
    *,
    temperature: float | None,
    num_predict: int | None,
    stream: bool,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "keep_alive": -1,
        "think": False,
    }

    options: dict[str, Any] = {}
    num_ctx = get_int("OLLAMA_NUM_CTX", 0)

    if num_ctx > 0:
        options["num_ctx"] = num_ctx

    if temperature is not None:
        options["temperature"] = temperature

    if num_predict is not None:
        options["num_predict"] = num_predict

    if options:
        body["options"] = options

    return body


def ask_ollama(prompt: str, *, temperature: float | None = None) -> tuple[str, str]:
    url = _ollama_url()
    model = get_env("OLLAMA_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL

    response = requests.post(
        f"{url}/api/generate",
        json=_generate_body(prompt, model, temperature=temperature, num_predict=None, stream=False),
        timeout=get_int("OLLAMA_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
    )

    response.raise_for_status()

    return response.json().get("response", "").strip(), model


def stream_ollama(
    prompt: str,
    *,
    temperature: float | None = None,
    num_predict: int | None = None,
    on_text: Callable[[str], None] | None = None,
    stop: Callable[[str], bool] | None = None,
) -> tuple[str, str]:
    """Resposta em streaming. `on_text` recebe o texto acumulado a cada pedaço e
    `stop` pode encerrar a geração: fechar a conexão faz o Ollama abortá-la."""

    url = _ollama_url()
    model = get_env("OLLAMA_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL
    body = _generate_body(prompt, model, temperature=temperature, num_predict=num_predict, stream=True)
    text = ""

    with requests.post(
        f"{url}/api/generate",
        json=body,
        timeout=get_int("OLLAMA_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
        stream=True,
    ) as response:
        response.raise_for_status()

        for raw in response.iter_lines():
            if not raw:
                continue

            chunk = json.loads(raw)
            piece = chunk.get("response") or ""

            if piece:
                text += piece

                if on_text:
                    on_text(text)

                if stop and stop(text):
                    break

            if chunk.get("done"):
                break

    return text.strip(), model


CHANNEL_BY_SOURCE = {"mqtt": "mqtt", "voice": "voice"}


def answer_question(
    question: str,
    *,
    source: str = "api",
    persona_id: str | None = None,
    on_text: Callable[[str], None] | None = None,
    cancel: threading.Event | None = None,
) -> dict[str, Any]:
    """Responde uma pergunta usando o estado atual e o histórico.

    A persona é a pedida explicitamente; senão, a configurada para o canal.
    Com `source="voice"` a resposta é curta (ver `copilot/voice.py`) e, se
    `on_text` for dado, recebe o texto parcial já cortado conforme o LLM escreve;
    `cancel` interrompe a geração (o cliente foi embora).
    """

    request_id = str(uuid4())
    started = time.monotonic()
    model = None
    voice_mode = source == "voice"
    persona = resolve_persona(persona_id, channel=CHANNEL_BY_SOURCE.get(source, "web"))

    record(
        "otterpilot",
        service="otterpilot",
        component="copilot",
        event_type="request_received",
        message="Pergunta recebida pelo OtterPilot",
        question=question,
        request_id=request_id,
        source=source,
        persona=persona.id,
    )

    try:
        current = build_voice_context(question) if voice_mode else build_current_context()
        history = get_historical_context(question, request_id)
        prompt = build_prompt(question, current, history, persona, voice_mode=voice_mode)

        def clean_up(text: str) -> str:
            # Persona "família": palavrões viram palavras neutras antes de mostrar ou falar.
            return soften(text) if persona.family_friendly else text

        if voice_mode:

            def relay(partial: str) -> None:
                if on_text:
                    on_text(voice.trim_voice(clean_up(partial)))

            answer, model = stream_ollama(
                prompt,
                temperature=persona.temperature,
                num_predict=voice.NUM_PREDICT,
                on_text=relay,
                stop=lambda text: bool(cancel and cancel.is_set()) or voice.voice_enough(text),
            )
            answer = voice.trim_voice(clean_up(answer))
        else:
            answer, model = ask_ollama(prompt, temperature=persona.temperature)
            answer = clean_up(answer)

        ok = True

        record(
            "otterpilot",
            service="otterpilot",
            component="copilot",
            event_type="response_generated",
            message="Resposta gerada pelo OtterPilot",
            question=question,
            answer=answer,
            request_id=request_id,
            duration_ms=round((time.monotonic() - started) * 1000),
            model=model,
            source=source,
            persona=persona.id,
        )

    except NotConfiguredError as error:
        ok = False
        answer = f"O Copilot ainda não está configurado: {error}."

    except Exception as error:
        ok = False
        answer = f"Erro ao consultar o OtterPilot: {error}"

        record(
            "otterpilot",
            service="otterpilot",
            component="copilot",
            event_type="error",
            severity="error",
            status="error",
            message="Erro ao processar pergunta",
            question=question,
            request_id=request_id,
            error=str(error),
            source=source,
        )

    return {
        "request_id": request_id,
        "timestamp": now_iso(),
        "question": question,
        "answer": answer,
        "ok": ok,
        "model": model,
        "persona": {"id": persona.id, "name": persona.name},
        "duration_ms": round((time.monotonic() - started) * 1000),
    }
