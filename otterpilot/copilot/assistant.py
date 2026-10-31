"""Interface MQTT do Copilot (perguntas e respostas para o Home Assistant)."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from otterpilot.copilot.service import answer_question
from otterpilot.core.serialization import make_json_safe
from otterpilot.integrations.mqtt.client import run_subscriber

LEGACY_REQUEST_TOPIC = "homelab/lontranoc/request"
LEGACY_RESPONSE_TOPIC = "homelab/lontranoc/response"

REQUEST_TOPIC = "otterpilot/request"
RESPONSE_TOPIC = "otterpilot/response"

RESPONSE_TOPICS = {
    LEGACY_REQUEST_TOPIC: LEGACY_RESPONSE_TOPIC,
    REQUEST_TOPIC: RESPONSE_TOPIC,
}

# Uma pergunta por vez: o LLM é o gargalo, e responder fora do callback
# mantém o keepalive MQTT vivo durante gerações longas.
_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="copilot")


def parse_question(payload_text: str) -> str:
    try:
        data = json.loads(payload_text)
    except ValueError:
        return payload_text.strip()

    if isinstance(data, dict):
        return str(data.get("question", "")).strip()

    return str(data).strip()


def _answer_and_publish(client, question: str, response_topic: str) -> None:
    result = answer_question(question, source="mqtt")

    payload = {
        "request_id": result["request_id"],
        "timestamp": result["timestamp"],
        "question": result["question"],
        "answer": result["answer"],
    }

    client.publish(
        response_topic,
        json.dumps(make_json_safe(payload), ensure_ascii=False),
    )


def on_message(client, msg):
    response_topic = RESPONSE_TOPICS.get(msg.topic)

    if response_topic is None:
        return

    question = parse_question(msg.payload.decode(errors="replace"))

    if not question:
        return

    _worker.submit(_answer_and_publish, client, question, response_topic)


def topics() -> list[tuple[str, int]]:
    return [(topic, 0) for topic in RESPONSE_TOPICS]


def main():
    run_subscriber("copilot-mqtt", topics, on_message)


if __name__ == "__main__":
    main()
