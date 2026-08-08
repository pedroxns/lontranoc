import json
import os
import time
from datetime import datetime, timezone
from xmlrpc import client
from otterpilot.core.config import get_env
from otterpilot.routing.query_context import build_query_context

import paho.mqtt.client as mqtt
import requests
from uuid import uuid4
from otterpilot.knowledge.providers.openobserve.ingest import emit
from otterpilot.knowledge.providers.openobserve.search import search_logs
from otterpilot.routing.context_router import route_context
from otterpilot.knowledge.search import search_context, build_search_summary
from otterpilot.analysis.engine import analyze_search_result
from otterpilot.core.serialization import make_json_safe
from otterpilot.state import build_default_state_store

OLLAMA_URL = get_env("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = get_env("OLLAMA_MODEL", "qwen2.5:7b-instruct")

MQTT_HOST = get_env("MQTT_HOST")
MQTT_PORT = int(get_env("MQTT_PORT", "1883"))

LEGACY_REQUEST_TOPIC = "homelab/lontranoc/request"
LEGACY_RESPONSE_TOPIC = "homelab/lontranoc/response"

REQUEST_TOPIC = "otterpilot/request"
RESPONSE_TOPIC = "otterpilot/response"

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def should_use_graylog(question: str) -> bool:
    q = question.lower()

    keywords = [
        "hoje",
        "ontem",
        "últimas",
        "ultimas",
        "últimos",
        "ultimos",
        "horas",
        "histórico",
        "historico",
        "aconteceu",
        "ocorreu",
        "erro",
        "falha",
        "caiu",
        "queda",
        "lento",
        "lentidão",
        "lentidao",
        "temperatura máxima",
        "temperatura maxima",
        "piorou",
        "mudou",
    ]

    return any(k in q for k in keywords)

def get_historical_context(question: str, request_id: str):
    result = search_context(question)
    analysis = analyze_search_result(result)
    summary = build_search_summary(result)
    ctx = result["context"]

    if not result["valid"] and not result["error"]:
        return []

    if result["error"]:
        emit(
            stream="otterpilot",
            service="otterpilot",
            component="assistant",
            event_type="search_error",
            severity="error",
            status="error",
            message="Erro ao consultar OpenObserve",
            request_id=request_id,
            searched_stream=summary["stream"],
            query_name=summary["query_name"],
            route_score=summary["route_score"],
            time_label=summary["time_label"],
            error=result["error"],
            schema_version="1.0",
        )

        return [{"error": result["error"]}]

    emit(
        stream="otterpilot",
        service="otterpilot",
        component="assistant",
        event_type="search_executed",
        message="Consulta histórica executada no OpenObserve",
        request_id=request_id,
        searched_stream=summary["stream"],
        query_name=summary["query_name"],
        route_score=summary["route_score"],
        time_label=summary["time_label"],
        time_expression=summary["time_expression"],
        time_confidence=summary["time_confidence"],
        time_granularity=summary["time_granularity"],
        result_count=summary["result_count"],
        incident_count=len(analysis.get("incidents", [])),
        schema_version="1.0",
    )

    return {
        "search_summary": summary,
        "analysis": analysis,
        "sample_events": result["rows"][:5],
    }

def get_current_context() -> dict:
    store = build_default_state_store()

    states = store.list_all()

    system_health = None
    resources = []

    for state in states:
        if (
            state["connector"] == "otterpilot"
            and state["capability"] == "system_health"
            and state["resource_id"] == "homelab"
        ):
            system_health = state
            continue

        resources.append(
            {
                "connector": state["connector"],
                "capability": state["capability"],
                "resource_id": state["resource_id"],
                "status": state["status"],
                "severity": state["severity"],
                "timestamp": state["timestamp"],
                "message": state["message"],
                "payload": state["payload"],
            }
        )

    return {
        "system_health": system_health,
        "resources": resources,
    }

def ask_ollama(question, context, request_id):
    historical_events = get_historical_context(question, request_id)
    prompt = f"""
    Você é o OtterPilot, um copiloto inteligente para homelabs, infraestrutura self-hosted e pequenos ambientes de TI.

    Seu objetivo é ajudar o usuário a compreender o estado do ambiente, correlacionar eventos, identificar problemas e sugerir ações práticas.

    Você nunca inventa informações.
    Sempre utiliza primeiro os dados coletados do ambiente.
    Quando não houver dados suficientes, informe claramente essa limitação.

    O bloco "Estado atual do ambiente" representa o estado corrente conhecido dos recursos monitorados.
    O bloco "Eventos históricos do OpenObserve" representa eventos e ocorrências históricas recuperados para a pergunta.

    Estado atual do ambiente:
    {json.dumps(make_json_safe(context), indent=2, ensure_ascii=False)}

    Eventos históricos do OpenObserve:
    {json.dumps(make_json_safe(historical_events), indent=2, ensure_ascii=False)}

    Pergunta:
    {question}

    Responda em português do Brasil, de forma correta e bem-humorada.
    Seja técnico, útil, sarcástico e irônico quando apropriado.
    Pode ser direto e levemente rude, mas nunca às custas da precisão técnica ou da clareza.
    Não invente dados.
    Não trate inferências como fatos.
    Se houver alerta, destaque claramente.
    """

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "24h",
        },
        timeout=120,
    )

    response.raise_for_status()
    return response.json().get("response", "").strip()


def publish_response(
    client,
    question,
    answer,
    request_id,
    response_topic: str = RESPONSE_TOPIC,
):
    payload = {
        "request_id": request_id,
        "timestamp": now_iso(),
        "question": question,
        "answer": answer,
    }

    client.publish(
        response_topic,
        json.dumps(
            make_json_safe(payload),
            ensure_ascii=False,
        ),
    )


def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe(LEGACY_REQUEST_TOPIC)
    client.subscribe(REQUEST_TOPIC)


def on_message(client, userdata, msg):
    topic = msg.topic
    payload_text = msg.payload.decode()

    if msg.topic == LEGACY_REQUEST_TOPIC:
        response_topic = LEGACY_RESPONSE_TOPIC
    else:
        response_topic = RESPONSE_TOPIC

    if topic in (REQUEST_TOPIC, LEGACY_REQUEST_TOPIC):
        try:
            data = json.loads(payload_text)
            question = data.get("question", "").strip()
        except Exception:
            question = payload_text.strip()

        if not question:
            return

        request_id = str(uuid4())

        emit(
            stream="otterpilot",
            service="otterpilot",
            component="assistant",
            event_type="request_received",
            message="Pergunta recebida pelo OtterPilot",
            question=question,
            request_id=request_id,
        )


        try:
            start = time.time()
            current_context = get_current_context()
            answer = ask_ollama(
                question,
                current_context,
                request_id,
            )
            
            duration_ms = int((time.time() - start) * 1000)

            emit(
                stream="otterpilot",
                service="otterpilot",
                component="assistant",
                event_type="response_generated",
                message="Resposta gerada pelo OtterPilot",
                question=question,
                answer=answer,
                request_id=request_id,
                duration_ms=duration_ms,
                model=OLLAMA_MODEL,
            )
        except Exception as error:
            answer = f"Erro ao consultar o OtterPilot: {error}"

            emit(
                stream="otterpilot",
                service="otterpilot",
                component="assistant",
                event_type="error",
                severity="error",
                status="error",
                message="Erro ao processar pergunta",
                question=question,
                request_id=request_id,
                error=str(error),
                schema_version="1.0"
            ) 

        publish_response(
            client,
            question,
            answer,
            request_id,
            response_topic=response_topic,
        )


def main():
    while True:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            print("OtterPilot Assistant escutando MQTT...")
            client.loop_forever()
        except Exception as error:
            print(f"Erro MQTT no OtterPilot: {error}. Tentando novamente em 10s...")
            try:
                client.disconnect()
            except Exception:
                pass
            time.sleep(10)


if __name__ == "__main__":
    main()
