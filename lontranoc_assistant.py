import json
import os
import time
from datetime import datetime, timezone
from query_context import build_query_context

import paho.mqtt.client as mqtt
import requests
from dotenv import load_dotenv
from uuid import uuid4
from openobserve_ingest import emit
from openobserve_search import search_logs
from context_router import route_context
from search_engine import search_context, build_search_summary
from analysis_engine import analyze_search_result

load_dotenv("/opt/lontranoc/.env")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")

MQTT_HOST = os.getenv("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

REQUEST_TOPIC = "homelab/lontranoc/request"
RESPONSE_TOPIC = "homelab/lontranoc/response"

CONTEXT_TOPICS = [
    "homelab/status/raw",
    "homelab/ollama/status",
]

context_messages = {}


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
            stream="lontranoc",
            service="lontranoc",
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
        stream="lontranoc",
        service="lontranoc",
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

def ask_ollama(question, context, request_id):
    historical_events = get_historical_context(question, request_id)
    prompt = f"""
Você é o LontraNOC, operador técnico de um homelab amador.

Ambiente monitorado:
- matx_cpu = ryzen5 5600g - servidor Proxmox principal com RTX 3060 e Ollama.
- mitx_cpu = ryzen4 4600g - servidor Frigate com Google Coral.
- mini_cpu = intel n150 - servidor Beelink Mini.
- rack_temp = temperatura interna do rack.
- ups_status = estado do nobreak Intelbras.
- ups_battery = carga da bateria do nobreak.
- z2m_1 e z2m_2 = instâncias Zigbee2MQTT. z2m1 - roda no mATX e z2m2 roda no mITX.
- frigate = sistema de monitoramento por câmeras.
- ollama_status = estado do serviço de IA.
- ollama_latency = latência da IA.
- gpu_temp = temperatura da GPU.
- gpu_mem = uso de memória da GPU.


Dados atuais via MQTT:
{json.dumps(context, indent=2, ensure_ascii=False)}

Eventos históricos do OpenObserve:
{json.dumps(historical_events, indent=2, ensure_ascii=False)}

Pergunta:
{question}

Responda em português do Brasil, de forma correta e erudita.
Seja técnico, útil e sarcástico e ironico.
Não invente dados.
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


def publish_response(client, question, answer):
    payload = {
        "timestamp": now_iso(),
        "question": question,
        "answer": answer,
    }

    result = client.publish(
        RESPONSE_TOPIC,
        json.dumps(payload, ensure_ascii=False),
        qos=1,
        retain=True,
    )

    result.wait_for_publish(timeout=10)


def on_connect(client, userdata, flags, reason_code, properties):
    for topic in CONTEXT_TOPICS:
        client.subscribe(topic)

    client.subscribe(REQUEST_TOPIC)


def on_message(client, userdata, msg):
    topic = msg.topic
    payload_text = msg.payload.decode()

    if topic in CONTEXT_TOPICS:
        try:
            context_messages[topic] = json.loads(payload_text)
        except Exception:
            context_messages[topic] = payload_text
        return

    if topic == REQUEST_TOPIC:
        try:
            data = json.loads(payload_text)
            question = data.get("question", "").strip()
        except Exception:
            question = payload_text.strip()

        if not question:
            return

        request_id = str(uuid4())

        emit(
            stream="lontranoc",
            service="lontranoc",
            component="assistant",
            event_type="request_received",
            message="Pergunta recebida pelo LontraNOC",
            question=question,
            request_id=request_id,
        )


        try:
            start = time.time()
            answer = ask_ollama(question, context_messages, request_id)
            duration_ms = int((time.time() - start) * 1000)

            emit(
                stream="lontranoc",
                service="lontranoc",
                component="assistant",
                event_type="response_generated",
                message="Resposta gerada pelo LontraNOC",
                question=question,
                answer=answer,
                request_id=request_id,
                duration_ms=duration_ms,
                model=OLLAMA_MODEL,
            )
        except Exception as error:
            answer = f"Erro ao consultar o LontraNOC: {error}"

            emit(
                stream="lontranoc",
                service="lontranoc",
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

        publish_response(client, question, answer)


def main():
    while True:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        client.on_connect = on_connect
        client.on_message = on_message

        try:
            client.connect(MQTT_HOST, MQTT_PORT, 60)
            print("LontraNOC Assistant escutando MQTT...")
            client.loop_forever()
        except Exception as error:
            print(f"Erro MQTT no LontraNOC: {error}. Tentando novamente em 10s...")
            try:
                client.disconnect()
            except Exception:
                pass
            time.sleep(10)


if __name__ == "__main__":
    main()
