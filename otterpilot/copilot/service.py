from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import requests

from otterpilot.analysis.engine import analyze_search_result
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
            lines.append(
                f"- [{problem['impact']}] {problem['connector']}/{problem['capability']} "
                f"{problem['resource_id']}: {problem['reason']}"
            )

    lines.append("Recursos (connector/capability recurso: status | métricas):")

    for state in store.list_all():
        if state["capability"] == "system_health":
            continue

        metrics = _key_metrics(state["capability"], state["payload"])
        line = (
            f"- {state['connector']}/{state['capability']} {state['resource_id']}: "
            f"{state['status']}"
        )

        if metrics:
            line += f" | {metrics}"

        if _is_stale(state):
            line += f" | sem atualização há {_describe_age(state['timestamp'])}"

        lines.append(line)

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


def _history_text(history: dict[str, Any]) -> str:
    text = json.dumps(make_json_safe(history), indent=1, ensure_ascii=False)

    if len(text) > MAX_HISTORY_CHARS:
        text = text[:MAX_HISTORY_CHARS] + "\n... (truncado)"

    return text


def build_prompt(question: str, current: str, history: dict[str, Any]) -> str:
    return f"""
Você é o OtterPilot, um copiloto inteligente para homelabs, infraestrutura self-hosted e pequenos ambientes de TI.

Seu objetivo é ajudar o usuário a compreender o estado do ambiente, correlacionar eventos, identificar problemas e sugerir ações práticas.

Você nunca inventa informações.
Sempre utiliza primeiro os dados coletados do ambiente.
Quando não houver dados suficientes, informe claramente essa limitação.

O bloco "Estado atual do ambiente" representa o estado corrente conhecido dos recursos monitorados.
O bloco "Eventos históricos do OpenObserve" representa eventos e ocorrências históricas recuperados para a pergunta.

Estado atual do ambiente:
{current}

Eventos históricos do OpenObserve:
{_history_text(history)}

Pergunta:
{question}

Responda em português do Brasil, de forma correta e bem-humorada.
Seja técnico, útil, sarcástico e irônico quando apropriado.
Pode ser direto e levemente rude, mas nunca às custas da precisão técnica ou da clareza.
Não invente dados.
Não trate inferências como fatos.
Se houver alerta, destaque claramente.
"""


def ask_ollama(prompt: str) -> tuple[str, str]:
    url = get_env("OLLAMA_URL")

    if not url:
        raise NotConfiguredError("Ollama não configurado (OLLAMA_URL)")

    model = get_env("OLLAMA_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL

    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": -1,
        "think": False,
    }

    num_ctx = get_int("OLLAMA_NUM_CTX", 0)

    if num_ctx > 0:
        body["options"] = {"num_ctx": num_ctx}

    response = requests.post(
        f"{url.rstrip('/')}/api/generate",
        json=body,
        timeout=get_int("OLLAMA_TIMEOUT_SECONDS", 120),
    )

    response.raise_for_status()

    return response.json().get("response", "").strip(), model


def answer_question(
    question: str,
    *,
    source: str = "api",
) -> dict[str, Any]:
    """Responde uma pergunta usando o estado atual e o histórico."""

    request_id = str(uuid4())
    started = time.monotonic()
    model = None

    record(
        "otterpilot",
        service="otterpilot",
        component="copilot",
        event_type="request_received",
        message="Pergunta recebida pelo OtterPilot",
        question=question,
        request_id=request_id,
        source=source,
    )

    try:
        current = build_current_context()
        history = get_historical_context(question, request_id)
        answer, model = ask_ollama(build_prompt(question, current, history))
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
        "duration_ms": round((time.monotonic() - started) * 1000),
    }
